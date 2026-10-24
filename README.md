# Perebas Player — prova de conceito Orsay

Protótipo para testar **Hyprland/Wayland → PipeWire → H.264 → RTSP → Samsung Smart TV Legacy** na UN40FH5303G. O critério principal é a latência observada na TV física. Esta primeira etapa usa vídeo sem áudio e controle conectado ao PC. O script do desktop é Linux/Hyprland; o adaptador Windows e o retorno de controles da TV serão feitos somente se o caminho de vídeo passar no teste.

## Preparação

1. No Linux, instale PipeWire, WirePlumber, `xdg-desktop-portal-hyprland`, GStreamer com `pipewiresrc`, FFmpeg com codificador H.264 e Python 3 com PyGObject (`gi`). Verifique `gst-inspect-1.0 pipewiresrc` e `ffmpeg -encoders | rg h264_vaapi`. Neste computador há Intel UHD Raptor Lake, então o padrão do script é VAAPI; `--encoder nvenc` e `--encoder libx264` também estão disponíveis. Ter o codificador listado não garante que o driver consiga usá-lo.
2. [Instale o MediaMTX](https://mediamtx.org/docs/kickoff/install) e inicie `mediamtx` em outro terminal. Como alternativa de teste no Linux com Docker, use `docker run --rm --network host bluenviron/mediamtx:1`. Deixe o RTSP na porta 8554 e permita conexões de entrada do IP da TV na rede local. A publicação do FFmpeg segue a [documentação do MediaMTX](https://mediamtx.org/docs/publish/ffmpeg).
3. Descubra o IPv4 do **computador** na LAN (`ip -4 addr`). Coloque esse endereço em [tv/settings.js](tv/settings.js). O app da TV inicia a conexão com o PC, portanto o IP da **TV** pode mudar sem alterar a configuração. Se o IP do PC também mudar, configure uma reserva DHCP para ele no roteador ou use um nome DNS local resolvido pela TV. Confirme a resolução desse nome na TV real antes de substituir o IPv4. O PC e a TV devem alcançar um ao outro; cabo no PC é preferível para o teste.
4. Importe `tv/` como projeto de app **Samsung Smart TV Legacy / SDK 4.5**. Para gerar um ZIP simples, rode `bash scripts/package-tv.sh` e use o pacote `build/PerebasPlayer.zip` no fluxo de instalação de desenvolvimento do SDK. O pacote ainda precisa ser validado pelo SDK e na TV, pois eles não estão disponíveis nesta sessão. [Documentação de instalação/teste Legacy](https://developer.samsung.com/smarttv/legacy/development-guides/getting-started.html).

Para **Start App Sync** na TV de 2013, gere o ZIP com o IP real do notebook embutido no app e sirva-o na porta HTTP 80:

```bash
PEREBAS_PC_IP=192.168.15.6 bash scripts/package-tv.sh
PEREBAS_LAN_IP=192.168.15.6 sudo -E node scripts/serve-tv.js
```

Substitua pelo IP que você informou em **IP Setting**. Alternativa com Docker, sem `sudo`:

```bash
docker run -d --rm --name perebas-widget-server --network host \
  -v "$PWD:/app:ro" -w /app -e PEREBAS_LAN_IP=192.168.15.6 \
  node:24-bookworm-slim node scripts/serve-tv.js
docker logs -f perebas-widget-server
```

Verifique `http://<IP>/widgetlist.xml` no notebook; o servidor registra as requisições da TV. Com o servidor ativo, na TV acesse **Mais aplicativos → Opções → Start App Sync**. O servidor serve apenas `widgetlist.xml` e o ZIP, e pode ser encerrado após a instalação (`docker stop perebas-widget-server`). O resultado precisa ser validado na TV real.

O MAC da TV é opcional para o diagnóstico de rede do PC. Se quiser usá-lo, copie `.env.example` para `.env`, preencha `PEREBAS_TV_MAC` e carregue o arquivo com `set -a; . ./.env; set +a` antes de rodar `python3 desktop/tv_network.py`. O script procura o MAC no cache local de vizinhos e mostra o IP da TV **somente se o PC já a tiver visto na mesma rede**. O endereço real fica no `.env` ignorado pelo Git. O app Orsay não lê variáveis de ambiente do PC e não precisa do MAC para receber RTSP. A reserva DHCP relevante para manter o IP do fluxo está associada ao MAC da interface **cabeada do PC**.

## Primeiro ensaio

Execute no Hyprland, selecione o monitor quando o portal pedir autorização e mantenha o processo rodando. Escolha um perfil no PC:

```bash
python3 desktop/stream.py --mode game --encoder vaapi
# ou: python3 desktop/stream.py --mode film --encoder vaapi
```

| Perfil | Objetivo | Vídeo inicial | Codificação | Cache inicial na TV | Caminho RTSP |
|---|---|---|---|---|---|
| Jogo | Menor latência | 720p/60, 6 Mb/s | Sem quadros B, fila curta; `libx264` ultrafast/zerolatency | 100 ms | `perebas-game` |
| Filme | Maior qualidade | 1080p/30, 10 Mb/s | Mais tempo de codificação; `libx264` medium com quadros B | 1000 ms | `perebas-film` |

Os valores são pontos de partida, não garantias de reprodução ou latência. `--size`, `--fps` e `--bitrate` permitem ajustar após medir a TV. Para isolar problemas de captura, use `--test-pattern` (padrão gerado pelo GStreamer). Para testar sem codificação por hardware, use `--encoder libx264`. Confirme a publicação com `ffplay -rtsp_transport tcp rtsp://127.0.0.1:8554/perebas-game` (ou `perebas-film`) antes de abrir o app na TV; o atraso no `ffplay` **não** representa o atraso do player Samsung.

Na TV, ENTER inicia/para; VERDE alterna JOGO/FILME; VERMELHO alterna o cache do perfil (100/300 ms em jogo, 1000/2000 ms em filme) e reconecta. Para trocar o perfil **completo**, reinicie `desktop/stream.py` com o mesmo `--mode`; um perfil que não está sendo publicado não tocará. O painel mostra eventos de início/fim de buffering com tempos relativos. Se a TV não conectar, verifique o IP em `tv/settings.js`, a porta 8554, os logs do MediaMTX e os erros no painel. A [especificação RTSP da Samsung](https://d3unf4s5rp9dfh.cloudfront.net/SmartTV_Legacy/multimedia/streaming/RTSP%20Specification.pdf) documenta H.264 em RTP, transporte UDP/TCP e `|caching=<ms>`, mas a aplicação real desses recursos na UN40FH5303G precisa ser medida.

Estes são perfis **do fluxo e do app**. A opção de imagem “Modo Jogo” do menu da TV é uma configuração separada; não há evidência de que ela se aplique ao player de apps Orsay nesta TV. Compare a latência real com as opções de imagem disponíveis no aparelho.

## Medição

Abra [desktop/latency.html](desktop/latency.html) em tela cheia no monitor capturado. Filme **monitor e TV no mesmo quadro**, de preferência a 120 ou 240 fps. Em vários quadros da gravação, subtraia o valor em milissegundos da TV do valor no monitor: isso estima o atraso de vídeo, incluindo a diferença de varredura das duas telas. Use a tecla espaço para criar uma mudança visual clara e estimar entrada → TV. Faça um ensaio de 10 minutos e anote pausas, artefatos e deriva do atraso. Compare com HDMI, se disponível.

| Data/hora | Firmware | GPU/driver | Rede PC/TV | Resolução/fps | Encoder/bitrate | Cache TV | Atraso mediano/pior | Buffering/falhas em 10 min |
|---|---|---|---|---|---|---|---|---|
| A preencher | | | | 720p60 | VAAPI/6M | 300 ms | | |

Compare os dois perfis e os dois valores de cache de cada um. Depois tente 1080p60 (`--mode game --size 1920x1080`) se 720p60 funcionar. Se o app não aceitar o fluxo, registre se a falha ocorreu em RTSP, decodificação ou renderização. O emulador pode ajudar a verificar instalação e interface; a conclusão sobre latência exige a TV real.

## Estado

Nesta máquina, ensaios com MediaMTX em Docker e `--test-pattern --encoder libx264` publicaram os dois perfis: o `ffprobe` confirmou 720p/60 sem quadros B em jogo e 1080p/30 com dois quadros B em filme. A tentativa com VAAPI falhou ao inicializar o dispositivo (`unknown libva error`), então o driver de vídeo precisa ser verificado antes do teste com codificação por hardware. A captura via portal, o player na TV e a latência ainda não foram medidos. O SDK 4.5 não está instalado. Áudio, Windows e comandos do controle conectado à TV continuam fora desta primeira prova.
