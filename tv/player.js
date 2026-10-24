/* Samsung Smart TV Legacy / Orsay. Sem sintaxe JavaScript moderna. */
var Perebas = {
  player: null,
  mode: "game",
  cacheValues: { game: [100, 300], film: [1000, 2000] },
  cacheIndex: 0,
  startedAt: 0,
  bufferingAt: 0,
  playing: false,
  events: [],

  elapsed: function () { return new Date().getTime() - this.startedAt; },
  log: function (message) {
    var line = (this.elapsed() / 1000).toFixed(2) + "s: " + message;
    this.events.unshift(line);
    if (this.events.length > 5) this.events.pop();
    document.getElementById("events").innerHTML = this.events.join("<br>");
    if (window.console && console.log) console.log(line);
  },
  status: function (message) { document.getElementById("status").innerHTML = message; this.log(message); },
  url: function () {
    return "rtsp://" + PEREBAS_HOST + ":" + PEREBAS_PORT + "/" + PEREBAS_PATH +
      "-" + this.mode + "|caching=" + this.cacheValues[this.mode][this.cacheIndex];
  },
  details: function () {
    document.getElementById("details").innerHTML = "Modo: " +
      (this.mode === "game" ? "JOGO" : "FILME") + " &nbsp; " + this.url() +
      "<br>ENTER: iniciar/parar &nbsp; VERDE: modo &nbsp; VERMELHO: cache &nbsp; RETURN: parar";
  },
  init: function () {
    this.startedAt = new Date().getTime();
    this.player = document.getElementById("pluginPlayer");
    this.player.OnBufferingStart = "Perebas.onBufferingStart";
    this.player.OnBufferingComplete = "Perebas.onBufferingComplete";
    this.player.OnBufferingProgress = "Perebas.onBufferingProgress";
    this.player.OnStreamInfoReady = "Perebas.onStreamInfoReady";
    this.player.OnRenderingComplete = "Perebas.onRenderingComplete";
    this.player.OnRenderError = "Perebas.onRenderError";
    this.player.OnStreamNotFound = "Perebas.onStreamNotFound";
    this.player.OnConnectionFailed = "Perebas.onConnectionFailed";
    this.player.OnNetworkDisconnected = "Perebas.onNetworkDisconnected";
    document.onkeydown = function (event) { Perebas.onKey(event || window.event); };
    this.details();
    this.status("Pronto para conectar");
  },
  play: function () {
    try {
      this.player.SetDisplayArea(0, 0, 1280, 720);
      this.status("Conectando");
      this.player.Play(this.url());
      this.playing = true;
    } catch (e) { this.status("Falha ao abrir: " + e); }
  },
  stop: function () {
    if (this.player && this.playing) {
      try { this.player.Stop(); } catch (e) { this.log("Falha ao parar: " + e); }
    }
    this.playing = false;
    this.status("Parado");
  },
  onKey: function (event) {
    var key = event.keyCode;
    if (key === 13) { if (this.playing) this.stop(); else this.play(); }
    else if (key === 108 || key === 403) {
      this.cacheIndex = (this.cacheIndex + 1) % this.cacheValues[this.mode].length;
      this.details(); this.status("Cache: " + this.cacheValues[this.mode][this.cacheIndex] + " ms");
      if (this.playing) { this.stop(); this.play(); }
    } else if (key === 20 || key === 404) {
      var wasPlaying = this.playing;
      if (wasPlaying) this.stop();
      this.mode = this.mode === "game" ? "film" : "game";
      this.cacheIndex = 0;
      this.details(); this.status("Modo " + (this.mode === "game" ? "JOGO" : "FILME"));
      if (wasPlaying) this.play();
    } else if (key === 88 || key === 10009) this.stop();
  },
  onBufferingStart: function () { Perebas.bufferingAt = new Date().getTime(); Perebas.status("Buffering iniciado"); },
  onBufferingProgress: function (percent) { if (percent === 100) Perebas.log("Buffering 100%"); },
  onBufferingComplete: function () {
    Perebas.status("Buffering completo em " + (new Date().getTime() - Perebas.bufferingAt) + " ms");
  },
  onStreamInfoReady: function () { Perebas.status("Informações do fluxo recebidas"); },
  onRenderingComplete: function () { Perebas.status("Reprodução encerrada"); Perebas.playing = false; },
  onRenderError: function (code) { Perebas.status("Erro de renderização: " + code); },
  onStreamNotFound: function () { Perebas.status("Fluxo não encontrado"); },
  onConnectionFailed: function () { Perebas.status("Conexão RTSP falhou"); },
  onNetworkDisconnected: function () { Perebas.status("Rede desconectada"); }
};
