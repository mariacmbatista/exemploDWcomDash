-- =============================================================================
-- DATA WAREHOUSE MULTIDIMENSIONAL DE VENDAS 
-- Sistema Gerenciador: MySQL 8.0+
-- Autora: Profa. Ceça Moraes (UFRPE)
-- =============================================================================
DROP DATABASE IF EXISTS dw_vendas_db;
CREATE DATABASE dw_vendas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dw_vendas_db;
-- -----------------------------------------------------------------------------
-- 1. DIMENSÃO TEMPO (dim_tempo)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_tempo (
    id_tempo INT AUTO_INCREMENT PRIMARY KEY,
    data DATE NOT NULL UNIQUE,
    ano INT NOT NULL,
    mes INT NOT NULL,
    nome_mes VARCHAR(20) NOT NULL,
    dia INT NOT NULL,
    dia_semana VARCHAR(20) NOT NULL,
    trimestre VARCHAR(5) NOT NULL,
    semestre VARCHAR(5) NOT NULL,
    eh_fim_de_semana BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_tempo_data (data),
    INDEX idx_tempo_ano_mes (ano, mes)
) ENGINE = InnoDB;
-- -----------------------------------------------------------------------------
-- 2. DIMENSÃO PRODUTO (dim_produto)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_produto (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    cod_produto_origem VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(150) NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    subcategoria VARCHAR(80) NOT NULL,
    marca VARCHAR(80) NOT NULL,
    preco_unitario_tabela DECIMAL(10, 2) NOT NULL,
    custo_unitario_base DECIMAL(10, 2) NOT NULL,
    INDEX idx_prod_categoria (categoria),
    INDEX idx_prod_subcategoria (subcategoria)
) ENGINE = InnoDB;
-- -----------------------------------------------------------------------------
-- 3. DIMENSÃO CLIENTE & GEOGRAFIA (dim_cliente)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_cliente (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    cod_cliente_origem VARCHAR(50) NOT NULL,
    nome_cliente VARCHAR(150) NOT NULL,
    segmento VARCHAR(50) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    estado CHAR(2) NOT NULL,
    regiao VARCHAR(30) NOT NULL,
    INDEX idx_cli_regiao (regiao),
    INDEX idx_cli_estado (estado),
    INDEX idx_cli_segmento (segmento)
) ENGINE = InnoDB;
-- -----------------------------------------------------------------------------
-- 4. DIMENSÃO CANAL DE VENDA (dim_canal)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_canal (
    id_canal INT AUTO_INCREMENT PRIMARY KEY,
    canal_venda VARCHAR(60) NOT NULL,
    tipo_operacao VARCHAR(40) NOT NULL,
    modalidade_frete_padrao VARCHAR(50) NOT NULL
) ENGINE = InnoDB;
-- -----------------------------------------------------------------------------
-- 5. TABELA FATO: fato_vendas (Centro do Modelo Estrela)
-- -----------------------------------------------------------------------------
CREATE TABLE fato_vendas (
    id_fato BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_tempo INT NOT NULL,
    id_produto INT NOT NULL,
    id_cliente INT NOT NULL,
    id_canal INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario_praticado DECIMAL(10, 2) NOT NULL,
    valor_bruto DECIMAL(12, 2) NOT NULL,
    desconto DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    valor_liquido DECIMAL(12, 2) NOT NULL,
    custo_total DECIMAL(12, 2) NOT NULL,
    lucro_liquido DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_fato_tempo FOREIGN KEY (id_tempo) REFERENCES dim_tempo(id_tempo),
    CONSTRAINT fk_fato_produto FOREIGN KEY (id_produto) REFERENCES dim_produto(id_produto),
    CONSTRAINT fk_fato_cliente FOREIGN KEY (id_cliente) REFERENCES dim_cliente(id_cliente),
    CONSTRAINT fk_fato_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal),
    INDEX idx_fato_pesquisa (id_tempo, id_produto, id_cliente, id_canal)
) ENGINE = InnoDB;
-- -----------------------------------------------------------------------------
-- 6. DADOS INICIAIS DE EXEMPLO
-- -----------------------------------------------------------------------------
INSERT INTO dim_canal (
        canal_venda,
        tipo_operacao,
        modalidade_frete_padrao
    )
VALUES ('E-commerce Web', 'Digital', 'Correios Sedex'),
    ('App Mobile', 'Digital', 'Expressa Mesma Dia'),
    ('Loja Física', 'Presencial', 'Retirada em Loja'),
    ('Marketplace', 'Indireto', 'Logística Parceira'),
    ('Televendas', 'Direto', 'Transportadora');
INSERT INTO dim_produto (
        cod_produto_origem,
        nome_produto,
        categoria,
        subcategoria,
        marca,
        preco_unitario_tabela,
        custo_unitario_base
    )
VALUES (
        'PROD-001',
        'Smartphone Pro Max 256GB',
        'Eletrônicos',
        'Smartphones',
        'TechBrand',
        4500.00,
        3100.00
    ),
    (
        'PROD-002',
        'Notebook Gamer 16GB SSD 1TB',
        'Informática',
        'Notebooks',
        'ApexCorp',
        5800.00,
        4200.00
    ),
    (
        'PROD-003',
        'Smart TV 55 Polegadas 4K OLED',
        'Eletrônicos',
        'Smart TVs',
        'VisionPlus',
        3900.00,
        2750.00
    ),
    (
        'PROD-004',
        'Cadeira Ergonômica Mesh',
        'Móveis',
        'Cadeiras',
        'ComfyWork',
        1200.00,
        750.00
    ),
    (
        'PROD-005',
        'Geladeira Frost Free Inverter 450L',
        'Eletrodomésticos',
        'Geladeiras',
        'EletroMax',
        4200.00,
        2900.00
    ),
    (
        'PROD-006',
        'Monitor UltraWide 34 Pol 144Hz',
        'Informática',
        'Monitores',
        'ApexCorp',
        2800.00,
        1950.00
    );
INSERT INTO dim_cliente (
        cod_cliente_origem,
        nome_cliente,
        segmento,
        cidade,
        estado,
        regiao
    )
VALUES (
        'CLI-001',
        'Empresa Tech Recife Ltda',
        'Corporativo (B2B)',
        'Recife',
        'PE',
        'Nordeste'
    ),
    (
        'CLI-002',
        'Livraria Paulista SA',
        'Corporativo (B2B)',
        'São Paulo',
        'SP',
        'Sudeste'
    ),
    (
        'CLI-003',
        'João Carlos da Silva',
        'Consumidor Final',
        'Curitiba',
        'PR',
        'Sul'
    ),
    (
        'CLI-004',
        'Consultoria Brasília DF',
        'Pequenas Empresas',
        'Brasília',
        'DF',
        'Centro-Oeste'
    ),
    (
        'CLI-005',
        'Maria Antônia Fernandes',
        'Consumidor Final',
        'Salvador',
        'BA',
        'Nordeste'
    ),
    (
        'CLI-006',
        'Inovação Manaus Tech',
        'Corporativo (B2B)',
        'Manaus',
        'AM',
        'Norte'
    );