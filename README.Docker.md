# Python, dbt e BigQuery -- containerização com Docker

Projeto sendo containerizado com Docker para fácil execução e portabilidade.

# Pré-requisitos
Docker - versão 29.8.0 ou superior

# Como executar o Projeto
Siga os passos abaixo para rodar a aplicação usando Docker Build

## 1. Clonar o repositório
Abre o terminal e clone o projeto
```bash
git clone https://github.com/guscrat/jaffle-shop-analytics-bigquery.git
```

## 2. Criar imagem Docker
Execute o comando abaixo para criar uma imagem desse projeto em seu Docker
```bash
docker build -t nome-da-imagem
```

## 3. Criar e executar um container
O comando abaixo cria um container e executa o conteúdo da imagem construida
```bash
docker run -d --name nome-do-container nome-da-imagem
```

## 4. Para verificar as logs do container
```bash
docker logs nome-do-container
```

# Conclusão
Esse é um commit inicial que monta o projeto de analytics do repositorio em um container, nos proximos commits haverão atualizações para execução das transformações de dados com dbt, utilizando BigQuery como cloud storage.