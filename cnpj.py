# -*- encoding: utf-8 -*-
import os
import glob
import sys
import csv
import datetime
import sqlalchemy
import pandas as pd

from cfwf import read_cfwf

REGISTROS_TIPOS = {
    '1':'empresas',
    '2':'socios',
    '6':'cnaes_secundarios'
}

EMPRESAS_COLUNAS = [
    'cnpj',
    'matriz_filial',     
    'razao_social',      
    'nome_fantasia',     
    'situacao',          
    'data_situacao',     
    'motivo_situacao',   
    'nm_cidade_exterior',
    'cod_pais',          
    'nome_pais',         
    'cod_nat_juridica',  
    'data_inicio_ativ',  
    'cnae_fiscal',       
    'tipo_logradouro',   
    'logradouro',        
    'numero',            
    'complemento',       
    'bairro',            
    'cep',               
    'uf',                
    'cod_municipio',     
    'municipio',         
    'ddd_1',             
    'telefone_1',        
    'ddd_2',             
    'telefone_2',        
    'ddd_fax',           
    'num_fax',           
    'email',             
    'qualif_resp',       
    'capital_social',    
    'porte',             
    'opc_simples',       
    'data_opc_simples',  
    'data_exc_simples',  
    'opc_mei',           
    'sit_especial',      
    'data_sit_especial'
]

EMPRESAS_COLSPECS = [
    (3, 17), 
    (17 ,18 ),
    (18 ,168),
    (168,223),
    (223,225),
    (225,233),
    (233,235),
    (235,290),
    (290,293),
    (293,363),
    (363,367),
    (367,375),
    (375,382),
    (382,402),
    (402,462),
    (462,468),
    (468,624),
    (624,674),
    (674,682),
    (682,684),
    (684,688),
    (688,738),
    (738,742),
    (742,750),
    (750,754),
    (754,762),
    (762,766),
    (766,774),
    (774,889),
    (889,891),
    (891,905),
    (905,907),
    (907,908),
    (908,916),
    (916,924),
    (924,925),
    (925,948),
    (948,956)
]

EMPRESAS_DTYPE = {} # 'capital_social':float}

SOCIOS_COLUNAS = [
    'cnpj',
    'tipo_socio',      
    'nome_socio',       
    'cnpj_cpf_socio',   
    'cod_qualificacao', 
    'perc_capital',     
    'data_entrada',     
    'cod_pais_ext',     
    'nome_pais_ext',    
    'cpf_repres',       
    'nome_repres',      
    'cod_qualif_repres'
]

SOCIOS_COLSPECS = [
    (3, 17),      
    (17 ,18 ),
    (18 ,168),
    (168,182),
    (182,184),
    (184,189),
    (189,197),
    (197,200),
    (200,270),
    (270,281),
    (281,341),
    (341,343)
]

SOCIOS_DTYPE = {} # 'perc_capital':float}

CNAES_COLUNAS = ['cnpj'] + [num for num in range(99)]
CNAES_COLSPECS = [(3,17)] + [(num*7+17,num*7+24) for num in range(99)]

HEADER_COLUNAS = [
    'Nome do arquivo',
    'Data de gravacao',
    'Numero da remessa'
]

HEADER_COLSPECS = [
    (17,28),
    (28,36),
    (36,44)
]

TRAILLER_COLUNAS = [
    'Total de registros de empresas',
    'Total de registros de socios',
    'Total de registros de CNAEs secundarios',
    'Total de registros incluindo header e trailler'
]

TRAILLER_COLSPECS = [
    (17,26),
    (26,35),
    (35,44),
    (44,55)
]

# (<nome_do_indice>,<tabela>,<coluna>)
INDICES = [
    ('empresas_cnpj', REGISTROS_TIPOS['1'], EMPRESAS_COLUNAS[0]),
    ('empresas_raiz', REGISTROS_TIPOS['1'], 'substr({},0,9)'.format(EMPRESAS_COLUNAS[0])),
    ('socios_cnpj', REGISTROS_TIPOS['2'], SOCIOS_COLUNAS[0]),
    ('socios_cpf_cnpj', REGISTROS_TIPOS['2'], SOCIOS_COLUNAS[3]),
    ('socios_nome', REGISTROS_TIPOS['2'], SOCIOS_COLUNAS[2]),
    ('cnaes_cnpj', REGISTROS_TIPOS['6'], CNAES_COLUNAS[0])
]

PREFIXO_INDICE = 'ix_'

CHUNKSIZE=200000

NOME_ARQUIVO_SQLITE = 'CNPJ_full.db'

def cnpj_full(input_list, tipo_output, output_path):
    total_empresas = 0
    controle_empresas = 0
    total_socios = 0
    controle_socios = 0
    total_cnaes = 0
    controle_cnaes = 0
    
    if tipo_output in ['csv','sqlite']:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

    if tipo_output == 'sqlite':
        import sqlite3
        #from sqlalchemy.dialects.sqlite import dialect
        conBD = sqlite3.connect(os.path.join(output_path,NOME_ARQUIVO_SQLITE))

    if tipo_output == 'firebird':
        from sqlalchemy import create_engine
        #engine = create_engine('firebird+fdb://SYSDBA:masterkey@192.168.0.5/'+NOME_ARQUIVO_FIREBIRD)
        engine = create_engine(output_path)
        conBD = engine.connect()

    EMPRESAS_COLUNAS_DT = dict([
        ('cnpj',sqlalchemy.types.CHAR(length=14)),
        ('matriz_filial',sqlalchemy.types.CHAR(length=1)),
        ('razao_social',sqlalchemy.types.VARCHAR(length=160)),
        ('nome_fantasia',sqlalchemy.types.VARCHAR(length=80)),
        ('situacao',sqlalchemy.types.CHAR(length=2)),
        ('data_situacao',sqlalchemy.types.CHAR(length=8)),
        ('motivo_situacao',sqlalchemy.types.CHAR(length=2)),
        ('nm_cidade_exterior',sqlalchemy.types.VARCHAR(length=80)),
        ('cod_pais',sqlalchemy.types.CHAR(length=3)),
        ('nome_pais',sqlalchemy.types.VARCHAR(length=80)),
        ('cod_nat_juridica',sqlalchemy.types.CHAR(length=4)),
        ('data_inicio_ativ',sqlalchemy.types.CHAR(length=8)),
        ('cnae_fiscal',sqlalchemy.types.CHAR(length=7)),
        ('tipo_logradouro',sqlalchemy.types.VARCHAR(length=25)),
        ('logradouro',sqlalchemy.types.VARCHAR(length=80)),
        ('numero',sqlalchemy.types.VARCHAR(length=8)),
        ('complemento',sqlalchemy.types.VARCHAR(length=160)),
        ('bairro',sqlalchemy.types.VARCHAR(length=60)),
        ('cep',sqlalchemy.types.CHAR(length=8)),
        ('uf',sqlalchemy.types.CHAR(length=2)),
        ('cod_municipio',sqlalchemy.types.CHAR(length=4)),
        ('municipio',sqlalchemy.types.VARCHAR(length=80)),
        ('ddd_1',sqlalchemy.types.VARCHAR(length=6)),
        ('telefone_1',sqlalchemy.types.VARCHAR(length=10)),
        ('ddd_2',sqlalchemy.types.VARCHAR(length=6)),
        ('telefone_2',sqlalchemy.types.VARCHAR(length=10)),
        ('ddd_fax',sqlalchemy.types.VARCHAR(length=6)),
        ('num_fax',sqlalchemy.types.VARCHAR(length=10)),
        ('email',sqlalchemy.types.VARCHAR(length=120)),
        ('qualif_resp',sqlalchemy.types.CHAR(length=2)),
        ('capital_social',sqlalchemy.types.NUMERIC(precision=18, scale=2)),
        ('porte',sqlalchemy.types.CHAR(length=2)),
        ('opc_simples',sqlalchemy.types.CHAR(length=1)),
        ('data_opc_simples',sqlalchemy.types.CHAR(length=8)),
        ('data_exc_simples',sqlalchemy.types.CHAR(length=8)),
        ('opc_mei',sqlalchemy.types.CHAR(length=1)),
        ('sit_especial',sqlalchemy.types.VARCHAR(length=40)),
        ('data_sit_especial',sqlalchemy.types.CHAR(length=8))])

    SOCIOS_COLUNAS_DT = dict([
        ('cnpj',sqlalchemy.types.CHAR(length=14)),
        ('tipo_socio',sqlalchemy.types.CHAR(length=1)),
        ('nome_socio',sqlalchemy.types.VARCHAR(length=160)),
        ('cnpj_cpf_socio',sqlalchemy.types.CHAR(length=14)),
        ('cod_qualificacao',sqlalchemy.types.CHAR(length=2)),
        ('perc_capital',sqlalchemy.types.FLOAT()),
        ('data_entrada',sqlalchemy.types.CHAR(length=8)),
        ('cod_pais_ext',sqlalchemy.types.CHAR(length=3)),
        ('nome_pais_ext',sqlalchemy.types.VARCHAR(length=80)),
        ('cpf_repres',sqlalchemy.types.CHAR(length=11)),
        ('nome_repres',sqlalchemy.types.VARCHAR(length=80)),
        ('cod_qualif_repres',sqlalchemy.types.CHAR(length=2))])
    
    CNAES_COLUNAS_DT = dict([
        ('cnpj',sqlalchemy.types.CHAR(length=14)),
        ('cnae_ordem',sqlalchemy.types.INTEGER()),
        ('cnae',sqlalchemy.types.CHAR(length=7))])

    # Itera sobre sequencia de arquivos (p/ suportar arquivo dividido pela RF)
    for i_arq, arquivo in enumerate(input_list):
        print('Processando arquivo: {}'.format(arquivo))

        dados = read_cfwf(arquivo, 
                          type_width=1, 
                          colspecs= {'0':HEADER_COLSPECS,
                                     '1':EMPRESAS_COLSPECS,
                                     '2':SOCIOS_COLSPECS,
                                     '6':CNAES_COLSPECS,
                                     '9':TRAILLER_COLSPECS},
                          names={'0':HEADER_COLUNAS,
                                 '1':EMPRESAS_COLUNAS, 
                                 '2':SOCIOS_COLUNAS,
                                 '6':CNAES_COLUNAS,
                                 '9':TRAILLER_COLUNAS},
                          dtype={'1': EMPRESAS_DTYPE,
                                 '2': SOCIOS_DTYPE},
                          chunksize=CHUNKSIZE,
                          encoding='ISO-8859-15')

        # Itera sobre blocos (chunks) do arquivo
        for i_bloco, bloco in enumerate(dados):
            print('Processando bloco {}: até linha {}.'.format(i_bloco+1,
                                                               (i_bloco+1)*CHUNKSIZE), 
                  end='\r')

            for tipo_registro, df in bloco.items():

                if tipo_registro == '1': # empresas
                    total_empresas += len(df)

                    # Troca datas zeradas por vazio
                    df['data_opc_simples'] = (df['data_opc_simples']
                            .where(df['data_opc_simples'] != '0000-00-00',''))
                    df['data_exc_simples'] = (df['data_exc_simples']
                            .where(df['data_exc_simples'] != '0000-00-00',''))
                    df['data_sit_especial'] = (df['data_sit_especial']
                            .where(df['data_sit_especial'] != '0000-00-00',''))

                elif tipo_registro == '2': # socios
                    total_socios += len(df)
                    
                    # Troca cpf invalido por vazio
                    df['cpf_repres'] = (df['cpf_repres']
                            .where(df['cpf_repres'] != '***000000**',''))
                    df['nome_repres'] = (df['nome_repres']
                            .where(df['nome_repres'] != 'CPF INVALIDO',''))  

                    # Se socio for tipo 1 (cnpj), deixa campo intacto, do contrario, 
                    # fica apenas com os ultimos 11 digitos
                    df['cnpj_cpf_socio'] = (df['cnpj_cpf_socio']
                            .where(df['tipo_socio'] == '1',
                                   df['cnpj_cpf_socio'].str[-11:]))

                elif tipo_registro == '6': # cnaes_secundarios       
                    total_cnaes += len(df)

                    # Verticaliza tabela de associacao de cnaes secundarios,
                    # mantendo apenas os validos (diferentes de 0000000)
                    df = pd.melt(df, 
                                 id_vars=[CNAES_COLUNAS[0]], 
                                 value_vars=range(99),
                                 var_name='cnae_ordem', 
                                 value_name='cnae')

                    df = df[df['cnae'] != '0000000']

                elif tipo_registro == '0': # header
                    print('\nINFORMACOES DO HEADER:')

                    header = df.iloc[0,:]

                    for k, v in header.items():
                        print('{}: {}'.format(k, v))

                    # Para evitar que tente armazenar dados de header
                    continue

                elif tipo_registro == '9': # trailler
                    print('\nINFORMACOES DE CONTROLE:')

                    trailler = df.iloc[0,:]

                    controle_empresas = int(trailler['Total de registros de empresas'])
                    controle_socios = int(trailler['Total de registros de socios'])
                    controle_cnaes = int(trailler['Total de registros de CNAEs secundarios'])

                    print('Total de registros de empresas: {}'.format(controle_empresas))
                    print('Total de registros de socios: {}'.format(controle_socios))
                    print('Total de registros de CNAEs secundarios: {}'.format(controle_cnaes))
                    print('Total de registros incluindo header e trailler: {}'.format(
                            int(trailler['Total de registros incluindo header e trailler'])))

                    # Para evitar que tente armazenar dados de trailler
                    continue

                if tipo_output == 'csv':
                    if (i_arq + i_bloco) > 0:
                        replace_append = 'a'
                        header=False
                    else:
                        replace_append = 'w'
                        header=True

                    nome_arquivo_csv = REGISTROS_TIPOS[tipo_registro] + '.csv'
                    df.to_csv(os.path.join(output_path,nome_arquivo_csv), 
                              header=header,
                              mode=replace_append,
                              index=False,
                              quoting=csv.QUOTE_NONNUMERIC)

                elif tipo_output in ['sqlite','firebird']:
                    replace_append = 'append' if (i_arq + i_bloco) > 0 else 'replace' 

                    if tipo_registro == '1':
                        df.to_sql(REGISTROS_TIPOS[tipo_registro], 
                                  con=conBD, 
                                  if_exists=replace_append, 
                                  index=False,
                                  dtype=EMPRESAS_COLUNAS_DT)
                    elif tipo_registro == '2':
                        df.to_sql(REGISTROS_TIPOS[tipo_registro], 
                                  con=conBD, 
                                  if_exists=replace_append, 
                                  index=False,
                                  dtype=SOCIOS_COLUNAS_DT)
                    elif tipo_registro == '6':
                        df.to_sql(REGISTROS_TIPOS[tipo_registro], 
                                  con=conBD, 
                                  if_exists=replace_append, 
                                  index=False,
                                  dtype=CNAES_COLUNAS_DT)
                    else:
                        df.to_sql(REGISTROS_TIPOS[tipo_registro], 
                                  con=conBD, 
                                  if_exists=replace_append, 
                                  index=False)


    if tipo_output in ['sqlite', 'firebird']:
        conBD.close()

    # Imprime totais
    print('\nConversao concluida. Validando quantidades:')

    inconsistente = False

    print('Total de registros de empresas: {}'.format(total_empresas), end=' ')
    if total_empresas == controle_empresas:
        print('ok')
    else:
        print('!INCONSISTENTE!')
        inconsistente = True

    print('Total de registros de socios: {}'.format(total_socios), end=' ')
    if total_socios == controle_socios:
        print('ok')
    else:
        print('!INCONSISTENTE!')
        inconsistente = True

    print('Total de registros de CNAEs: {}'.format(total_cnaes), end=' ')
    if total_cnaes == controle_cnaes:
        print('ok')
    else:
        print('!INCONSISTENTE!')
        inconsistente = True


    if inconsistente:
        print(u'Atencao! Foi detectada inconsistencia entre as quantidades lidas e as informacoes de controle do arquivo.')

    if tipo_output == 'csv':
        print(u'Arquivos CSV gerados na pasta {}.'.format(output_path))

    elif tipo_output == 'sqlite':
        print(u'''
Arquivo SQLITE gerado: {}
OBS: Uso de índices altamente recomendado!
              '''.format(os.path.join(output_path,NOME_ARQUIVO_SQLITE)))


def cnpj_index(output_path):
    import sqlite3    

    conBD = sqlite3.connect(os.path.join(output_path,NOME_ARQUIVO_SQLITE))

    print(u'''
Criando índices...
Essa operaçao pode levar vários minutos.
    ''')

    cursorBD = conBD.cursor()

    for indice in INDICES:
        nome_indice = PREFIXO_INDICE + indice[0]

        sql_stmt = 'CREATE INDEX {} ON {} ({});'.format(nome_indice, indice[1], indice[2])
        cursorBD.execute(sql_stmt)

        print(u'Index {} criado.'.format(nome_indice))

    print(u'Indices criados com sucesso.')

    conBD.close()


def help():
    print('''
Uso: python cnpj.py <path_input> <output:csv|sqlite|firebird> <path_output> [--dir] [--noindex]
Argumentos opcionais:
 [--dir]: Indica que o <path_input> e uma pasta e pode conter varios ZIPs.
 [--noindex]: NAO gera indices automaticamente no sqlite ao final da carga.

Exemplos: python cnpj.py "data/F.K032001K.D81106D" sqlite "output"
          python cnpj.py "data" sqlite "output" --dir
          python cnpj.py "data" sqlite "output" --dir --noindex
          python cnpj.py "data" csv "output" --dir
    ''')


def main():

    num_argv = len(sys.argv)
    if num_argv < 4:
        help()
        sys.exit(-1)
    else:
        input_path = sys.argv[1]
        tipo_output = sys.argv[2]
        output_path = sys.argv[3]

        gera_index = True
        input_list = [input_path]

        if num_argv > 4:
            for opcional in sys.argv[4:num_argv]:
                if (opcional == '--noindex'):
                    gera_index = False
                elif (opcional == '--dir'):
                    input_list = glob.glob(os.path.join(input_path,'*.zip'))
                    input_list.sort()
                elif (opcional == '--createfdb'):
                    criar_fdb = True
                else:
                    print(u'Argumento opcional inválido.')
                    help()
                    break

        if tipo_output not in ['csv','sqlite','firebird']:
            print('''
Erro: tipo de output inválido. 
Escolha um dos seguintes tipos de output: csv ou sqlite.
            ''')
            help()

        else:
            print('Iniciando processamento em {}'.format(datetime.datetime.now()))

            cnpj_full(input_list, tipo_output, output_path)

            if (gera_index) and (tipo_output == 'sqlite'):
                cnpj_index(output_path)

            print('Processamento concluido em {}'.format(datetime.datetime.now()))

if __name__ == "__main__":
    main()
