#!/bin/bash

set -e

mkdir -p data/download data/output

CONNECTIONS=4
DOWNLOAD_URL="https://receita.economia.gov.br/orientacao/tributaria/cadastros/cadastro-nacional-de-pessoas-juridicas-cnpj/dados-publicos-cnpj"
FILE_URLS=$(wget --quiet --no-check-certificate -O - "$DOWNLOAD_URL" \
	| grep --color=no DADOS_ABERTOS_CNPJ \
	| grep --color=no ".zip" \
	| sed 's/.*"http:/http:/; s/".*//' \
	| sort)
MIRROR_URL="https://data.brasil.io/mirror/socios-brasil"
if [ "$1" = "--use-mirror" ]; then
	USE_MIRROR=true
else
	USE_MIRROR=false
fi

for url in $FILE_URLS; do
	if $USE_MIRROR; then
		url="$MIRROR_URL/$(basename $url)"
	fi
	time aria2c --auto-file-renaming=false --continue=true -s $CONNECTIONS -x $CONNECTIONS --dir=data/download "$url"
done

find ./ -type f -name '*.py' -exec sed -i 's/codigo_qualificacao_representante_legal/codigo_qualificacao_rep_legal/g' {} \;
find ./ -type f -name '*.csv' -exec sed -i 's/codigo_qualificacao_representante_legal/codigo_qualificacao_rep_legal/g' {} \;
find ./ -type f -name '*.py' -exec sed -i 's/CODIGO QUALIFICACAO REPRESENTANTE LEGAL/CODIGO QUALIFICACAO REP LEGAL/g' {} \;
find ./ -type f -name '*.csv' -exec sed -i 's/CODIGO QUALIFICACAO REPRESENTANTE LEGAL/CODIGO QUALIFICACAO REP LEGAL/g' {} \;
time python3.7 extract_dump.py data/output/ data/download/DADOS_ABERTOS_CNPJ*.zip --no_censorship
time python3.7 extract_partner_companies.py data/output/socio.csv.gz data/output/empresa-socia.csv.gz