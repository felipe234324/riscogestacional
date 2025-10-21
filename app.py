from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
import sqlite3
import json
import re
import uuid
from datetime import datetime
from init_db import criar_banco
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as ImageReader
import logging

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Criar o banco de dados
criar_banco()

# Registrar a fonte personalizada para o PDF
try:
    pdfmetrics.registerFont(TTFont('Poppins', 'static/fonts/Poppins-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Poppins-Bold', 'static/fonts/Poppins-Bold.ttf'))
except Exception as e:
    logging.error(f"Erro ao registrar fontes Poppins: {str(e)}")

# Mapeamentos de chaves internas para rótulos
CARACTERISTICAS_MAP = {
    '15anos': '≤ 15 anos',
    '40anos': '≥ 40 anos',
    'nao_aceita_gravidez': 'Não aceitação da gravidez',
    'violencia_domestica': 'Indícios de Violência Doméstica',
    'rua_indigena_quilombola': 'Situação de rua / indígena ou quilombola',
    'sem_escolaridade': 'Sem escolaridade',
    'tabagista_ativo': 'Tabagista ativo',
    'raca_negra': 'Raça negra'
}

AVALIACAO_NUTRICIONAL_MAP = {
    'baixo_peso': 'Baixo Peso (IMC < 18.5)',
    'sobrepeso': 'Sobrepeso (IMC 25-29.9)',
    'obesidade1': 'Obesidade Grau I e II (IMC 30-39.9)',
    'obesidade_morbida': 'Obesidade Mórbida (IMC ≥ 40)'
}

COMORBIDADES_MAP = {
    'aids_hiv': 'AIDS/HIV',
    'alteracoes_tireoide': 'Alterações da tireoide (hipotireoidismo sem controle e hipertireoidismo)',
    'diabetes_mellitus': 'Diabetes Mellitus',
    'endocrinopatias': 'Endocrinopatias sem controle',
    'cardiopatia': 'Cardiopatia diagnosticada',
    'cancer': 'Câncer Diagnosticado',
    'cirurgia_bariatrica': 'Cirurgia Bariátrica há menos de 1 ano',
    'doencas_autoimunes': 'Doenças Autoimunes (colagenoses)',
    'doencas_psiquiatricas': 'Doenças Psiquiátricas (Encaminhar ao CAPS)',
    'doenca_renal': 'Doença Renal Grave',
    'dependencia_drogas': 'Dependência de Drogas (Encaminhar ao CAPS)',
    'epilepsia': 'Epilepsia e doenças neurológicas graves de difícil controle',
    'hepatites': 'Hepatites (encaminhar ao infectologista)',
    'has_controlada': 'HAS crônica controlada (Sem hipotensor e exames normais)',
    'has_complicada': 'HAS crônica complicada',
    'ginecopatia': 'Ginecopatia (Miomatose ≥ 7cm, malformação uterina, massa anexial ≥ 8cm ou com características complexas)',
    'pneumopatia': 'Pneumopatia grave de difícil controle',
    'tuberculose': 'Tuberculose em tratamento ou com diagnóstico na gestação (Encaminhar ao Pneumologista)',
    'trombofilia': 'Trombofilia ou Tromboembolia',
    'teratogenico': 'Uso de medicações com potencial efeito teratogênico',
    'varizes': 'Varizes acentuadas',
    'doencas_hematologicas': 'Doenças hematológicas (PTI, Anemia Falciforme, PTT, Coagulopatias, Talassemias)',
    'transplantada': 'Transplantada em uso de imunossupressor'
}

HISTORIA_OBSTETRICA_MAP = {
    'abortamentos': '2 abortamentos espontâneos consecutivos ou 3 não consecutivos (confirmados clínico/laboratorial)',
    'abortamentos_consecutivos': '3 ou mais abortamentos espontâneos consecutivos',
    'prematuros': 'Mais de um Prematuro com menos de 36 semanas',
    'obito_fetal': 'Óbito Fetal sem causa determinada',
    'preeclampsia': 'Pré-eclâmpsia ou Pré-eclâmpsia superposta',
    'eclampsia': 'Eclâmpsia',
    'hipertensao_gestacional': 'Hipertensão Gestacional',
    'acretismo': 'Acretismo placentário',
    'descolamento_placenta': 'Descolamento prematuro de placenta',
    'insuficiencia_istmo': 'Insuficiência Istmo Cervical',
    'restricao_crescimento': 'Restrição de Crescimento Intrauterino',
    'malformacao_fetal': 'História de malformação Fetal complexa',
    'isoimunizacao': 'Isoimunização em gestação anterior',
    'diabetes_gestacional': 'Diabetes gestacional',
    'psicose_puerperal': 'Psicose Puerperal',
    'tromboembolia': 'História de tromboembolia'
}

CONDICOES_GESTACIONAIS_MAP = {
    'ameaca_aborto': 'Ameaça de aborto - Encaminhar URGÊNCIA',
    'acretismo_placentario_atual': 'Acretismo Placentário',
    'placenta_previa': 'Placenta Pós',
    'anemia_grave': 'Anemia não responsiva à tratamento (Hb≤8) e hemopatia',
    'citologia_anormal': 'Citologia Cervical anormal (LIEAG) – Encaminhar para PTGI',
    'tireoide_gestacao': 'Doenças da tireoide diagnosticada na gestação',
    'diabetes_gestacional_atual': 'Diabetes gestacional',
    'doenca_hipertensiva': 'Doença Hipertensiva na Gestação (Pré-eclâmpsia, Hipertensão gestacional e Pré-eclâmpsia superada)',
    'doppler_anormal': 'Alteração no doppler das Artérias uterinas (aumento da resistência) e/ou alto risco para Pré-eclâmpsia',
    'doenca_hemolitica': 'Doença Hemolítica',
    'gemelar': 'Gemelar',
    'isoimunizacao_rh': 'Isoimunizacao Rh',
    'insuficiencia_istmo_atual': 'Insuficiência Istmo cervical',
    'colo_curto': 'Colo curto no morfológico 2T',
    'malformacao_congenita': 'Malformação Congênita Fetal',
    'neoplasia_cancer': 'Neoplasia ginecológica ou Câncer diagnosticado na gestação',
    'polidramnio_oligodramnio': 'Polidrâmnio/Oligodrâmnio',
    'restricao_crescimento': 'Restrição de crescimento fetal Intrauterino',
    'toxoplasmose': 'Toxoplasmose',
    'sifilis_complicada': 'Sífilis terciária, Alterações ultrassom sugestivas de sífilis neonatal ou resistência ao tratamento com Penicilina Benzatina',
    'infeccao_urinaria_repeticao': 'Infecção Urinária de repetição (pielonefrite ou ITU≥3x)',
    'hiv_htlv_hepatites': 'HIV, HTLV ou Hepatites Agudas',
    'condiloma_acuminado': 'Condiloma acuminado (no canal vaginal/colo ou lesões extensas em região genital/perianal)',
    'feto_percentil': 'Feto com percentil > P90 (GIG) ou entre P3-10 (PIG), com doppler normal',
    'hepatopatias': 'Hepatopatias (colestase ou aumento das transaminases)',
    'hanseníase': 'Hanseníase diagnosticada na gestação',
    'tuberculose_gestacao': 'Tuberculose diagnosticada na gestação',
    'dependencia_drogas_atual': 'Dependência e/ou uso abusivo de drogas lícitas e ilícitas'
}

def get_db_connection():
    conn = sqlite3.connect('banco.db')
    conn.row_factory = sqlite3.Row
    return conn

def draw_text(c, text, x, y, font='Helvetica', font_size=9, max_width=None, centered=False):
    if not text or not isinstance(text, str):
        text = "Não informado"
    try:
        c.setFont(font, font_size)
    except Exception as e:
        logging.warning(f"Erro ao definir fonte {font}: {str(e)}. Usando Helvetica.")
        c.setFont('Helvetica', font_size)
    if centered:
        c.drawCentredString(x, y, text)
        return y - (font_size + 2) - 5
    if max_width:
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if c.stringWidth(test_line, font, font_size) > max_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        for i, line in enumerate(lines):
            c.drawString(x, y - i * (font_size + 2), line)
        return y - len(lines) * (font_size + 2) - 5
    else:
        c.drawString(x, y, text)
        return y - (font_size + 1) - 5

def map_item(campo, item):
    if not item or item.strip() == '':
        return 'Não informado'
    mapping = {
        'caracteristicas': CARACTERISTICAS_MAP,
        'avaliacao_nutricional': AVALIACAO_NUTRICIONAL_MAP,
        'comorbidades': COMORBIDADES_MAP,
        'historia_obstetrica': HISTORIA_OBSTETRICA_MAP,
        'condicoes_gestacionais': CONDICOES_GESTACIONAIS_MAP
    }.get(campo, {})
    return mapping.get(item, item)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        profissional = request.form.get('profissional')
        if not profissional or profissional.strip() == '':
            flash('Por favor, insira o nome do profissional.', 'error')
            return redirect(url_for('login'))

        session['profissional'] = profissional.strip()
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('calculadora'))
    
    return render_template('login.html')

@app.route('/calculadora', methods=['GET'])
def calculadora():
    if 'profissional' not in session:
        flash('Por favor, faça login para acessar a calculadora.', 'error')
        return redirect(url_for('login'))
    return render_template('calculadora.html')

@app.route('/salvar_calculadora', methods=['POST'])
def salvar_calculadora():
    if 'profissional' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login para salvar os dados.'}), 401

    try:
        profissional = session['profissional']
        data = request.form

        # Validar campos obrigatórios
        nome_gestante = data.get('nome_gestante')
        data_nasc = data.get('data_nasc')
        cpf = data.get('cpf', '000.000.000-00')
        telefone = data.get('telefone')
        municipio = 'Itaquitinga'
        ubs = data.get('ubs')
        acs = data.get('acs')
        periodo_gestacional = data.get('periodo_gestacional')
        data_envio = data.get('data_envio', datetime.now().strftime('%d/%m/%Y'))
        pontuacao_total = data.get('pontuacao_total')
        classificacao_risco = data.get('classificacao_risco', 'Risco Habitual')
        imc = data.get('imc', None)

        def parse_json_field(field_name):
            field = data.get(field_name)
            if not field:
                return []
            try:
                return json.loads(field) if isinstance(field, str) else field
            except json.JSONDecodeError:
                return []

        caracteristicas = parse_json_field('caracteristicas')
        avaliacao_nutricional = parse_json_field('avaliacao_nutricional')
        comorbidades = parse_json_field('comorbidades')
        historia_obstetrica = parse_json_field('historia_obstetrica')
        condicoes_gestacionais = parse_json_field('condicoes_gestacionais')

        required_fields = {
            'Nome da Gestante': nome_gestante,
            'Data de Nascimento': data_nasc,
            'Telefone': telefone,
            'UBS': ubs,
            'ACS': acs,
            'Período Gestacional': periodo_gestacional,
            'Classificação de Risco': classificacao_risco
        }
        for field_name, field_value in required_fields.items():
            if not field_value or field_value.strip() == '':
                return jsonify({
                    'success': False,
                    'message': f'O campo "{field_name}" é obrigatório.'
                }), 400

        if cpf and cpf != '000.000.000-00':
            cpf = re.sub(r'[^\d]', '', cpf)
            if not re.match(r'^\d{11}$', cpf):
                return jsonify({
                    'success': False,
                    'message': 'CPF inválido. Deve conter exatamente 11 dígitos.'
                }), 400
        else:
            cpf = '000.000.000-00'

        try:
            pontuacao_total = int(pontuacao_total) if pontuacao_total and pontuacao_total.strip() else 0
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Pontuação total inválida.'
            }), 400

        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_nasc):
            return jsonify({
                'success': False,
                'message': 'Data de nascimento inválida. Use o formato DD/MM/YYYY.'
            }), 400

        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_envio):
            return jsonify({
                'success': False,
                'message': 'Data de envio inválida. Use o formato DD/MM/YYYY.'
            }), 400

        caracteristicas_json = json.dumps(caracteristicas)
        avaliacao_nutricional_json = json.dumps(avaliacao_nutricional)
        comorbidades_json = json.dumps(comorbidades)
        historia_obstetrica_json = json.dumps(historia_obstetrica)
        condicoes_gestacionais_json = json.dumps(condicoes_gestacionais)

        codigo_ficha = str(uuid.uuid4())[:8].upper()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO calculos (
                codigo_ficha, nome_gestante, data_nasc, cpf, telefone, municipio, ubs, acs,
                periodo_gestacional, data_envio, pontuacao_total, classificacao_risco, imc,
                caracteristicas, avaliacao_nutricional, comorbidades, historia_obstetrica,
                condicoes_gestacionais, profissional, ativo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            codigo_ficha, nome_gestante, data_nasc, cpf, telefone, municipio, ubs, acs,
            periodo_gestacional, data_envio, pontuacao_total, classificacao_risco,
            float(imc) if imc and imc.strip() else None,
            caracteristicas_json, avaliacao_nutricional_json, comorbidades_json,
            historia_obstetrica_json, condicoes_gestacionais_json, profissional, 1
        ))

        conn.commit()
        cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ?', (codigo_ficha,))
        ficha_salva = cursor.fetchone()
        conn.close()

        if not ficha_salva:
            return jsonify({
                'success': False,
                'message': 'Erro ao salvar a ficha no banco de dados.'
            }), 500

        return jsonify({
            'success': True,
            'codigo_ficha': codigo_ficha,
            'message': f'Ficha salva com sucesso! Código: {codigo_ficha}',
            'dados': {
                'nome_gestante': nome_gestante,
                'data_nasc': data_nasc,
                'cpf': cpf,
                'telefone': telefone,
                'municipio': municipio,
                'ubs': ubs,
                'acs': acs,
                'periodo_gestacional': periodo_gestacional,
                'data_envio': data_envio,
                'pontuacao_total': pontuacao_total,
                'classificacao_risco': classificacao_risco,
                'imc': imc,
                'caracteristicas': caracteristicas,
                'avaliacao_nutricional': avaliacao_nutricional,
                'comorbidades': comorbidades,
                'historia_obstetrica': historia_obstetrica,
                'condicoes_gestacionais': condicoes_gestacionais,
                'profissional': profissional
            }
        })

    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        logging.error(f"Erro de integridade: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro de integridade no banco de dados: {str(e)}'
        }), 500
    except sqlite3.OperationalError as e:
        conn.rollback()
        conn.close()
        logging.error(f"Erro operacional no banco: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        conn.rollback()
        conn.close()
        logging.error(f"Erro geral ao salvar: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar os dados: {str(e)}'
        }), 500

@app.route('/historico', methods=['GET'])
def historico():
    if 'profissional' not in session:
        flash('Por favor, faça login para acessar o histórico.', 'error')
        return redirect(url_for('login'))
    
    return render_template('historico.html')

@app.route('/buscar_historico', methods=['POST'])
def buscar_historico():
    if 'profissional' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login.'}), 401

    try:
        profissional = session['profissional']
        logging.debug(f"Buscando histórico para profissional: {profissional}")
        conn = get_db_connection()
        cursor = conn.cursor()
        page = request.form.get('page', 1, type=int)
        per_page = 100
        offset = (page - 1) * per_page
        nome_gestante = request.form.get('nome_gestante', '').strip().lower()
        codigo_ficha = request.form.get('codigo_ficha', '').strip().upper()
        data_inicio = request.form.get('data_inicio', '')
        data_fim = request.form.get('data_fim', '')

        query = '''
            SELECT id, codigo_ficha, nome_gestante, data_nasc, cpf, periodo_gestacional, data_envio, 
                   pontuacao_total, classificacao_risco, municipio
            FROM calculos
            WHERE profissional = ? AND ativo = 1 AND (nome_gestante LIKE ? OR ? = '') AND (codigo_ficha = ? OR ? = '')
        '''
        params = [profissional, f'%{nome_gestante}%', nome_gestante, codigo_ficha, codigo_ficha]

        if data_inicio:
            query += ' AND data_envio >= ?'
            params.append(data_inicio)
        if data_fim:
            query += ' AND data_envio <= ?'
            params.append(data_fim)

        query_count = f'SELECT COUNT(*) AS total FROM ({query}) AS subquery'
        cursor.execute(query_count, params)
        total_registros = cursor.fetchone()['total']
        logging.debug(f"Total de registros encontrados: {total_registros}")

        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])

        cursor.execute(query, params)
        registros = []
        for row in cursor.fetchall():
            registro = dict(row)
            registros.append(registro)
        logging.debug(f"Registros retornados: {registros}")

        conn.close()
        return jsonify({
            'success': True,
            'fichas': registros,
            'total_records': total_registros,
            'total_pages': (total_registros + per_page - 1) // per_page,
            'current_page': page
        })

    except sqlite3.OperationalError as e:
        conn.close()
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}'}), 500

@app.route('/obter_ficha_completa', methods=['POST'])
def obter_ficha_completa():
    if 'profissional' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login.'}), 401

    try:
        registro_id = request.form.get('registro_id')
        if not registro_id:
            return jsonify({'success': False, 'message': 'ID do registro inválido.'}), 400

        profissional = session['profissional']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM calculos WHERE id = ? AND profissional = ? AND ativo = 1
        ''', (registro_id, profissional))
        registro = cursor.fetchone()
        if not registro:
            conn.close()
            return jsonify({'success': False, 'message': 'Registro não encontrado.'}), 404

        registro_dict = dict(registro)
        for field in ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 'historia_obstetrica', 'condicoes_gestacionais']:
            try:
                if registro[field]:
                    items = json.loads(registro[field])
                    if not isinstance(items, list):
                        items = [items] if items else []
                    mapped_items = [map_item(field, item) for item in items if item and item.strip()]
                    registro_dict[field] = ', '.join(mapped_items) if mapped_items else 'Não informado'
                else:
                    registro_dict[field] = 'Não informado'
            except json.JSONDecodeError:
                registro_dict[field] = 'Não informado'

        conn.close()
        return jsonify({'success': True, 'registro': registro_dict})
    except sqlite3.OperationalError as e:
        conn.close()
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro no banco de dados: {str(e)}'}), 500

@app.route('/encerrar_registro_cpf', methods=['POST'])
def encerrar_registro_cpf():
    if 'profissional' not in session:
        return jsonify({'success': False, 'message': 'Por favor, faça login.'}), 401

    try:
        data = request.get_json()
        cpf = data.get('cpf')
        nome_gestante = data.get('nome_gestante')  # Opcional
        data_nasc = data.get('data_nasc')  # Opcional

        if not cpf:
            return jsonify({
                'success': False,
                'message': 'CPF é obrigatório.'
            }), 400

        # Validar CPF
        cpf_clean = re.sub(r'[^\d]', '', cpf)
        if not re.match(r'^\d{11}$', cpf_clean) and cpf != '000.000.000-00':
            return jsonify({
                'success': False,
                'message': 'CPF inválido. Deve conter exatamente 11 dígitos.'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se existem registros com o CPF fornecido
        cursor.execute('''
            SELECT COUNT(*) as count FROM calculos 
            WHERE cpf = ? AND profissional = ? AND ativo = 1
        ''', (cpf, session['profissional']))
        count = cursor.fetchone()['count']
        if count == 0:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Nenhum registro ativo encontrado para o CPF fornecido.'
            }), 404

        # Atualizar todos os registros com o mesmo CPF para ativo = 0
        cursor.execute('''
            UPDATE calculos SET ativo = 0
            WHERE cpf = ? AND profissional = ?
        ''', (cpf, session['profissional']))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Todos os registros com CPF {cpf} foram encerrados com sucesso.'
        })

    except sqlite3.OperationalError as e:
        conn.rollback()
        conn.close()
        logging.error(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro no banco de dados: {str(e)}'
        }), 500
    except Exception as e:
        conn.rollback()
        conn.close()
        logging.error(f"Erro ao encerrar registros: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao encerrar registros: {str(e)}'
        }), 500

@app.route('/gerar_pdf/<code>')
def gerar_pdf(code):
    if 'profissional' not in session:
        flash('Por favor, faça login para baixar o PDF.', 'error')
        return redirect(url_for('historico'))

    try:
        logging.debug(f"Iniciando geração de PDF para ficha {code} pelo profissional {session['profissional']}")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta com verificação de permissão
        cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ? AND profissional = ? AND ativo = 1', 
                       (code, session['profissional']))
        ficha = cursor.fetchone()

        if not ficha:
            cursor.execute('SELECT * FROM calculos WHERE codigo_ficha = ?', (code,))
            if cursor.fetchone():
                logging.warning(f"Ficha {code} existe, mas profissional {session['profissional']} não tem acesso")
            else:
                logging.warning(f"Ficha {code} não encontrada no banco")
            conn.close()
            flash('Ficha não encontrada ou você não tem acesso a ela.', 'error')
            return redirect(url_for('historico'))

        colunas = [desc[0] for desc in cursor.description]
        ficha_dict = dict(zip(colunas, ficha))
        conn.close()
        logging.debug(f"Dados da ficha: {ficha_dict}")

        # Processamento dos campos JSON
        campos_json = ['caracteristicas', 'avaliacao_nutricional', 'comorbidades', 
                       'historia_obstetrica', 'condicoes_gestacionais']
        mapped_data = {}

        for campo in campos_json:
            try:
                raw_value = ficha_dict.get(campo)
                logging.debug(f"Processando {campo} com valor bruto: {raw_value} (tipo: {type(raw_value)})")

                items = []
                if raw_value and isinstance(raw_value, str) and raw_value.strip():
                    try:
                        items = json.loads(raw_value)
                        if not isinstance(items, list):
                            items = [items] if items else []
                        items = [str(item).strip() for item in items if item and str(item).strip()]
                    except json.JSONDecodeError as e:
                        logging.warning(f"JSON inválido para {campo}: {raw_value} - {str(e)}")
                        items = [raw_value.strip()] if raw_value.strip() else []
                else:
                    items = []
                logging.debug(f"Itens após parsing para {campo}: {items}")

                # Processamento dos itens
                mapped_items = []
                for item in items:
                    mapped_item = map_item(campo, item)
                    if mapped_item and mapped_item != "Não informado":
                        mapped_items.append(mapped_item)

                mapped_data[campo] = mapped_items if mapped_items else ["Nenhum item selecionado."]
                logging.debug(f"Itens mapeados para {campo}: {mapped_data[campo]}")
            except Exception as e:
                logging.error(f"Erro ao processar {campo}: {str(e)}")
                mapped_data[campo] = ["Nenhum item selecionado."]

        # Configuração do PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin_left = 2 * cm
        margin_right = 2 * cm
        margin_top = 1.5 * cm
        margin_bottom = 2 * cm
        max_width = width - margin_left - margin_right
        total_pages = 1

        def check_page_space(c, y_position, required_space, total_pages):
            if y_position < margin_bottom + required_space:
                draw_footer(total_pages)
                c.showPage()
                draw_page_border()
                total_pages += 1
                logging.debug("Nova página criada devido a espaço insuficiente")
                return height - margin_top, total_pages
            return y_position, total_pages

        def draw_page_border():
            c.setStrokeColorRGB(0.2, 0.2, 0.2)
            c.setLineWidth(0.5)
            c.rect(
                margin_left - 10, 
                margin_bottom - 10, 
                width - margin_left - margin_right + 20, 
                height - margin_top - margin_bottom + 20
            )

        def draw_footer(page_number):
            c.saveState()
            c.setFont('Helvetica', 8)
            c.setFillColorRGB(0.5, 0.5, 0.5)
            footer_text = f"Página {page_number} | Gerado por Sistema de Classificação de Risco"
            c.drawCentredString(width / 2, margin_bottom - 20, footer_text)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(0.3)
            c.line(margin_left, margin_bottom - 5, width - margin_right, margin_bottom - 5)
            c.restoreState()

        y_position = height - margin_top
        logo_path = os.path.join('static', 'imagens', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader.open(logo_path)
            img_width = 140
            img_height = img_width * (img.height / img.width)
            c.drawImage(logo_path, (width - img_width) / 2, y_position - img_height, 
                        width=img_width, height=img_height, mask='auto')
            y_position -= img_height + 10
        else:
            logging.warning(f"Logo não encontrado em: {logo_path}")
            y_position -= 10

        y_position, total_pages = check_page_space(c, y_position, 60, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.5)
        c.rect(margin_left, y_position - 40, max_width, 40, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "SECRETARIA MUNICIPAL DE SAÚDE DE ITAQUITINGA", 
                              width / 2, y_position - 12, font='Helvetica', font_size=12, centered=True)
        y_position = draw_text(c, "INSTRUMENTO DE CLASSIFICAÇÃO DE RISCO GESTACIONAL - APS", 
                              width / 2, y_position, font='Helvetica', font_size=10, centered=True)
        y_position -= 10
        draw_page_border()

        y_position, total_pages = check_page_space(c, y_position, 40, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(margin_left, y_position - 20, max_width, 20, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "Dados da Gestante", margin_left + 10, y_position - 12, 
                              font='Helvetica', font_size=10, max_width=max_width - 20)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(margin_left, y_position, width - margin_right, y_position)
        y_position -= 15

        # Dados básicos
        dados_basicos = [
            f"Nome: {ficha_dict.get('nome_gestante', 'Não informado')}",
            f"Data de Nascimento: {ficha_dict.get('data_nasc', 'Não informado')}",
            f"CPF: {ficha_dict.get('cpf', 'Não informado')}",
            f"Telefone: {ficha_dict.get('telefone', 'Não informado')}",
            f"Município: {ficha_dict.get('municipio', 'Não informado')}",
            f"UBS: {ficha_dict.get('ubs', 'Não informado')}",
            f"ACS: {ficha_dict.get('acs', 'Não informado')}",
            f"Período Gestacional: {ficha_dict.get('periodo_gestacional', 'Não informado')}",
            f"Data de Envio: {ficha_dict.get('data_envio', 'Não informado')}",
            f"Código da Ficha: {ficha_dict.get('codigo_ficha', 'Não informado')}",
            f"IMC: {ficha_dict.get('imc', 'Não informado') if ficha_dict.get('imc') is not None else 'Não informado'}",
            f"Profissional: {ficha_dict.get('profissional', 'Não informado')}"
        ]
        logging.debug(f"Dados básicos para renderização: {dados_basicos}")

        col1_width = max_width / 2 - 10
        col2_width = col1_width
        col1_x = margin_left + 10
        col2_x = margin_left + col1_width + 20
        halfway = len(dados_basicos) // 2 + 1
        col1_items = dados_basicos[:halfway]
        col2_items = dados_basicos[halfway:]
        y_col1 = y_position
        y_col2 = y_position

        for i in range(max(len(col1_items), len(col2_items))):
            y_position, total_pages = check_page_space(c, min(y_col1, y_col2), 10, total_pages)
            if y_position != min(y_col1, y_col2):
                y_col1 = y_position
                y_col2 = y_position
            if i < len(col1_items):
                y_col1 = draw_text(c, col1_items[i], col1_x, y_col1, font='Helvetica', font_size=8, max_width=col1_width)
            if i < len(col2_items):
                y_col2 = draw_text(c, col2_items[i], col2_x, y_col2, font='Helvetica', font_size=8, max_width=col2_width)

        y_position = min(y_col1, y_col2) - 15

        secoes = [
            ("1. Características Individuais, Condições Socioeconômicas e Familiares", mapped_data['caracteristicas']),
            ("2. Avaliação Nutricional", mapped_data['avaliacao_nutricional']),
            ("3. Comorbidades Prévias à Gestação Atual", mapped_data['comorbidades']),
            ("4. Condições Clínicas Específicas e Relacionadas às Gestações Prévias", mapped_data['historia_obstetrica']),
            ("5. Condições Clínicas Específicas e Relacionadas à Gestação Atual", mapped_data['condicoes_gestacionais'])
        ]

        for titulo, itens in secoes:
            y_position, total_pages = check_page_space(c, y_position, 30, total_pages)
            c.setFillColorRGB(0.9, 0.9, 0.9)
            c.rect(margin_left, y_position - 18, max_width, 18, fill=1, stroke=1)
            c.setFillColorRGB(0, 0, 0)
            y_position = draw_text(c, titulo, margin_left + 10, y_position - 10, 
                                  font='Helvetica', font_size=9, max_width=max_width - 20)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.line(margin_left, y_position, width - margin_right, y_position)
            y_position -= 15

            for item in itens:
                y_position, total_pages = check_page_space(c, y_position, 15, total_pages)
                c.setFont('Helvetica', 8)
                bullet_y = y_position - 3
                c.circle(margin_left + 12, bullet_y, 1.5, stroke=1, fill=1)
                y_position = draw_text(c, item, margin_left + 20, y_position, 
                                      font='Helvetica', font_size=8, max_width=max_width - 20)
            y_position -= 10

        y_position, total_pages = check_page_space(c, y_position, 40, total_pages)
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(margin_left, y_position - 18, max_width, 18, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        y_position = draw_text(c, "Resultado", margin_left + 10, y_position - 10, 
                              font='Helvetica', font_size=9, max_width=max_width - 20)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(margin_left, y_position, width - margin_right, y_position)
        y_position -= 15
        y_position = draw_text(c, f"Pontuação Total: {ficha_dict.get('pontuacao_total', '0')}", 
                              margin_left + 10, y_position, font='Helvetica', font_size=9, max_width=max_width - 10)
        y_position = draw_text(c, f"Classificação de Risco: {ficha_dict.get('classificacao_risco', 'Não informado')}", 
                              margin_left + 10, y_position, font='Helvetica', font_size=9, max_width=max_width - 10)

        draw_footer(total_pages)
        c.save()
        buffer.seek(0)
        logging.debug(f"Tamanho do buffer do PDF: {len(buffer.getvalue())} bytes")

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"ficha_{code}.pdf",
            mimetype='application/pdf'
        )

    except sqlite3.OperationalError as e:
        if 'conn' in locals() and conn:
            conn.close()
        logging.error(f"Erro no banco de dados ao gerar PDF para ficha {code}: {str(e)}")
        flash('Erro ao acessar o banco de dados.', 'error')
        return redirect(url_for('historico'))
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        logging.exception(f"Erro ao gerar PDF para ficha {code}: {str(e)}")
        flash('Erro ao gerar o PDF.', 'error')
        return redirect(url_for('historico'))

@app.route('/logout', methods=['POST'])
def logout():
    if 'profissional' in session:
        session.pop('profissional', None)
        return jsonify({'success': True, 'message': 'Logout realizado com sucesso.'})
    return jsonify({'success': False, 'message': 'Nenhuma sessão ativa.'}), 401

if __name__ == '__main__':
    print(app.url_map)
    app.run(debug=True)