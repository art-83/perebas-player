#!/usr/bin/env python3
"""Hyprland portal -> PipeWire -> GStreamer -> FFmpeg -> MediaMTX (RTSP)."""

import argparse
import os
import shutil
import subprocess
import sys
import uuid

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gio, GLib, Gst  # noqa: E402

PORTAL_NAME = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
REQUEST = "org.freedesktop.portal.Request"
MODES = {
    "game": {"size": "1280x720", "fps": 60, "bitrate": "6M", "bufsize": "500k"},
    "film": {"size": "1920x1080", "fps": 30, "bitrate": "10M", "bufsize": "4M"},
}


class PortalCapture:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.session = None
        self.request_path = None
        self.answer = None
        self.loop = None
        self.subscription = self.bus.signal_subscribe(
            PORTAL_NAME, REQUEST, "Response", None, None,
            Gio.DBusSignalFlags.NONE, self._response)

    def _response(self, _bus, _sender, path, _iface, _signal, params):
        if path == self.request_path:
            self.answer = params.unpack()
            self.loop.quit()

    def request(self, method, signature, values):
        token = "perebas_" + uuid.uuid4().hex
        values[-1]["handle_token"] = GLib.Variant("s", token)
        result = self.bus.call_sync(
            PORTAL_NAME, PORTAL_PATH, SCREENCAST, method,
            GLib.Variant(signature, values), GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE, 10000, None)
        self.request_path = result.unpack()[0]
        self.answer = None
        self.loop = GLib.MainLoop()
        timeout_id = GLib.timeout_add_seconds(45, self._timeout)
        self.loop.run()
        if GLib.MainContext.default().find_source_by_id(timeout_id):
            GLib.source_remove(timeout_id)
        if self.answer is None or self.answer[0] != 0:
            raise RuntimeError("Portal cancelado, recusado ou sem resposta: " + str(self.answer))
        return self.answer[1]

    def _timeout(self):
        if self.answer is None:
            self.loop.quit()
        return False

    def open(self):
        created = self.request("CreateSession", "(a{sv})", [{
            "session_handle_token": GLib.Variant("s", "perebas_" + uuid.uuid4().hex)
        }])
        self.session = created["session_handle"]
        self.request("SelectSources", "(oa{sv})", [self.session, {
            "types": GLib.Variant("u", 1),  # monitor
            "multiple": GLib.Variant("b", False),
            "cursor_mode": GLib.Variant("u", 2),  # cursor embutido
        }])
        started = self.request("Start", "(osa{sv})", [self.session, "", {}])
        streams = started.get("streams", [])
        if not streams:
            raise RuntimeError("O portal não retornou um nó PipeWire")
        node = streams[0][0]
        result, fd_list = self.bus.call_with_unix_fd_list_sync(
            PORTAL_NAME, PORTAL_PATH, SCREENCAST, "OpenPipeWireRemote",
            GLib.Variant("(oa{sv})", (self.session, {})),
            GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, 10000, None, None)
        fd = fd_list.get(result.unpack()[0])
        return node, fd

    def close(self):
        if self.session:
            self.bus.call_sync(PORTAL_NAME, self.session,
                               "org.freedesktop.portal.Session", "Close", None,
                               None, Gio.DBusCallFlags.NONE, 3000, None)
        self.bus.signal_unsubscribe(self.subscription)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="IPv4 do MediaMTX")
    parser.add_argument("--port", type=int, default=8554)
    parser.add_argument("--path", default="perebas", help="prefixo: publica em <prefixo>-game ou <prefixo>-film")
    parser.add_argument("--mode", choices=MODES, default="game")
    parser.add_argument("--size", choices=["1280x720", "1920x1080"])
    parser.add_argument("--fps", type=int, choices=[30, 60])
    parser.add_argument("--encoder", choices=["vaapi", "nvenc", "libx264"], default="vaapi")
    parser.add_argument("--render-device", default="/dev/dri/renderD128")
    parser.add_argument("--bitrate")
    parser.add_argument("--test-pattern", action="store_true", help="isola a captura; não testa latência da tela")
    args = parser.parse_args()
    profile = MODES[args.mode]
    args.size = args.size or profile["size"]
    args.fps = args.fps or profile["fps"]
    args.bitrate = args.bitrate or profile["bitrate"]
    stream_path = args.path + "-" + args.mode
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and not args.test_pattern:
        parser.error("esta captura requer uma sessão Hyprland")
    for binary in ("ffmpeg", "gst-launch-1.0"):
        if not shutil.which(binary):
            parser.error(binary + " não encontrado")
    if args.encoder == "vaapi" and not os.path.exists(args.render_device):
        parser.error("dispositivo VAAPI ausente: " + args.render_device)

    width, height = map(int, args.size.split("x"))
    portal = None
    fd = None
    if not args.test_pattern:
        portal = PortalCapture()
        print("Selecione o monitor na janela de compartilhamento do Hyprland.", flush=True)
        node, fd = portal.open()
        source = ["pipewiresrc", "fd=" + str(fd), "path=" + str(node), "do-timestamp=true"]
    else:
        source = ["videotestsrc", "is-live=true", "pattern=ball"]

    gst = ["gst-launch-1.0", "-q", *source, "!", "queue",
           "max-size-buffers=2", "max-size-bytes=0", "max-size-time=0",
           "leaky=downstream", "!", "videoconvert", "!",
           "videoscale", "!", "videorate", "!",
           "video/x-raw,format=NV12,width=%d,height=%d,framerate=%d/1" %
           (width, height, args.fps), "!", "fdsink", "fd=1", "sync=false"]
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-f", "rawvideo",
          "-pix_fmt", "nv12", "-video_size", args.size, "-framerate", str(args.fps),
          "-i", "pipe:0", "-an"]
    if args.encoder == "vaapi":
        ff += ["-vaapi_device", args.render_device, "-vf", "format=nv12,hwupload",
               "-c:v", "h264_vaapi", "-bf", "0"]
    elif args.encoder == "nvenc":
        ff += ["-c:v", "h264_nvenc", "-preset", "p1" if args.mode == "game" else "p5",
               "-tune", "ull" if args.mode == "game" else "hq",
               "-bf", "0" if args.mode == "game" else "2"]
    else:
        ff += ["-c:v", "libx264", "-preset", "ultrafast" if args.mode == "game" else "medium",
               "-bf", "0" if args.mode == "game" else "2"]
        if args.mode == "game":
            ff += ["-tune", "zerolatency"]
    ff += ["-b:v", args.bitrate, "-maxrate", args.bitrate,
           "-bufsize", profile["bufsize"],
           "-g", str(args.fps if args.mode == "game" else args.fps * 2)]
    if args.encoder != "vaapi":
        ff += ["-pix_fmt", "yuv420p"]
    ff += ["-f", "rtsp", "-rtsp_transport", "tcp",
           "rtsp://%s:%d/%s" % (args.host, args.port, stream_path)]

    print("Publicando rtsp://%s:%d/%s (modo %s, %s, %s, %d fps)" %
          (args.host, args.port, stream_path, args.mode, args.encoder, args.size, args.fps), flush=True)
    capture = None
    encoder = None
    try:
        capture = subprocess.Popen(gst, stdout=subprocess.PIPE, pass_fds=(fd,) if fd else ())
        encoder = subprocess.Popen(ff, stdin=capture.stdout)
        capture.stdout.close()
        code = encoder.wait()
        if code:
            raise RuntimeError("FFmpeg terminou com código " + str(code))
    except KeyboardInterrupt:
        print("Encerrando...")
    finally:
        if encoder and encoder.poll() is None:
            encoder.terminate()
            encoder.wait()
        if capture and capture.poll() is None:
            capture.terminate()
            capture.wait()
        if fd is not None:
            os.close(fd)
        if portal:
            portal.close()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, GLib.Error) as error:
        print("Erro: " + str(error), file=sys.stderr)
        sys.exit(1)
