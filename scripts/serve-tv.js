// Servidor mínimo para a sincronização de widgets da Samsung Smart TV Legacy.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const ip = process.env.PEREBAS_LAN_IP;
const zip = path.resolve(__dirname, '..', 'build', 'PerebasPlayer.zip');
if (!ip || !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) {
  throw new Error('Defina PEREBAS_LAN_IP com o IPv4 do notebook na LAN');
}
if (!fs.existsSync(zip)) {
  throw new Error('Pacote ausente; rode bash scripts/package-tv.sh');
}

const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  console.log(new Date().toISOString(), req.socket.remoteAddress, req.method, pathname);
  res.setHeader('Cache-Control', 'no-store');
  if (pathname === '/widgetlist.xml') {
    const size = fs.statSync(zip).size;
    const xml = '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<rsp stat="ok"><list><widget id="PerebasPlayer">' +
      '<title>Perebas Player</title><compression type="zip" size="' + size + '"/>' +
      '<description>Prova de conceito RTSP</description>' +
      '<download>http://' + ip + '/widget/PerebasPlayer.zip</download>' +
      '</widget></list></rsp>\n';
    res.writeHead(200, {'Content-Type': 'text/xml; charset=utf-8', 'Content-Length': Buffer.byteLength(xml)});
    res.end(xml);
  } else if (pathname === '/widget/PerebasPlayer.zip') {
    res.writeHead(200, {'Content-Type': 'application/zip', 'Content-Length': fs.statSync(zip).size});
    if (req.method === 'HEAD') res.end();
    else fs.createReadStream(zip).pipe(res);
  } else {
    res.writeHead(404);
    res.end('Not found\n');
  }
});
server.listen(80, '0.0.0.0', () => console.log('Widget server: http://' + ip + '/widgetlist.xml'));
