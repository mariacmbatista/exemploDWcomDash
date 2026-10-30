import os
import random
import datetime
from sqlalchemy import create_engine, text
import pandas as pd

MYSQL_USER = os.getenv("DW_MYSQL_USER", "root")
MYSQL_PASS = os.getenv("DW_MYSQL_PASS", "")
MYSQL_HOST = os.getenv("DW_MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("DW_MYSQL_PORT", "3306")
MYSQL_DB   = os.getenv("DW_MYSQL_DB", "dw_vendas_db")

DB_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"

def popular_dim_tempo(engine, data_inicio='2024-01-01', data_fim='2026-12-31'):
    print("⏳ Populando dim_tempo...")
    datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
    
    dias_semana_pt = {
        0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
        3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
    }
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    registros = []
    for dt in datas:
        registros.append({
            'data': dt.strftime('%Y-%m-%d'),
            'ano': dt.year,
            'mes': dt.month,
            'nome_mes': meses_pt[dt.month],
            'dia': dt.day,
            'dia_semana': dias_semana_pt[dt.weekday()],
            'trimestre': f"T{(dt.month - 1) // 3 + 1}",
            'semestre': f"S{1 if dt.month <= 6 else 2}",
            'eh_fim_de_semana': 1 if dt.weekday() >= 5 else 0
        })
    
    df_tempo = pd.DataFrame(registros)
    df_tempo.to_sql('dim_tempo', con=engine, if_exists='append', index=False)
    print(f"✅ dim_tempo populada com {len(df_tempo)} dias.")

def popular_fato_vendas(engine, total_registros=3000):
    print(f"⏳ Gerando {total_registros} vendas para a fato_vendas...")
    with engine.connect() as conn:
        id_tempos = [r[0] for r in conn.execute(text("SELECT id_tempo FROM dim_tempo")).fetchall()]
        id_produtos = [r[0] for r in conn.execute(text("SELECT id_produto FROM dim_produto")).fetchall()]
        id_clientes = [r[0] for r in conn.execute(text("SELECT id_cliente FROM dim_cliente")).fetchall()]
        id_canais = [r[0] for r in conn.execute(text("SELECT id_canal FROM dim_canal")).fetchall()]
    
    if not id_tempos or not id_produtos or not id_clientes or not id_canais:
        print("❌ Erro: Dimensões vazias! Execute primeiro o script dw_schema_mysql.sql.")
        return

    fatos = []
    for _ in range(total_registros):
        id_t = random.choice(id_tempos)
        id_p = random.choice(id_produtos)
        id_c = random.choice(id_clientes)
        id_cn = random.choice(id_canais)
        
        qtd = random.randint(1, 12)
        preco_unit = round(random.uniform(80.0, 4500.0), 2)
        valor_bruto = round(qtd * preco_unit, 2)
        desc_pct = random.choice([0.0, 0.05, 0.10, 0.15])
        desconto = round(valor_bruto * desc_pct, 2)
        valor_liq = round(valor_bruto - desconto, 2)
        custo = round(valor_liq * random.uniform(0.60, 0.82), 2)
        lucro = round(valor_liq - custo, 2)
        
        fatos.append({
            'id_tempo': id_t,
            'id_produto': id_p,
            'id_cliente': id_c,
            'id_canal': id_cn,
            'quantidade': qtd,
            'preco_unitario_praticado': preco_unit,
            'valor_bruto': valor_bruto,
            'desconto': desconto,
            'valor_liquido': valor_liq,
            'custo_total': custo,
            'lucro_liquido': lucro
        })
        
    df_fatos = pd.DataFrame(fatos)
    df_fatos.to_sql('fato_vendas', con=engine, if_exists='append', index=False)
    print(f"🎉 fato_vendas populada com sucesso! Total: {len(df_fatos)} registros.")

if __name__ == "__main__":
    print(f"Conectando ao MySQL em {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}...")
    try:
        engine = create_engine(DB_URL)
        popular_dim_tempo(engine)
        popular_fato_vendas(engine, 3000)
    except Exception as e:
        print(f"⚠️ Erro ao popular MySQL: {e}")
