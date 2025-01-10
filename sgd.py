import mysql.connector
from mysql.connector import Error
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def connect_to_mariadb():
    try:
        # Conectando ao MariaDB
        connection = mysql.connector.connect(
            host='sgddolp.com',
            database='dolpenge_views',
            user='dolpenge_dolpviews',
            password='EuL7(s%MA4)fUZ,l0U'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Executando a consulta para pegar os dados de blitz e turnos
            query = """
            SELECT b.nome_inspetor, b.num_operacional, b.idtb_turnos, b.data_blitz, t.nom_fant, t.unidade
            FROM view_power_bi_blitz_contatos b
            JOIN view_power_bi_turnos t ON b.idtb_turnos = t.idtb_turnos
            """
            cursor.execute(query)
            resultados = cursor.fetchall()

            # Criando um DataFrame com os dados de blitz
            df = pd.DataFrame(resultados,
                              columns=["nome_inspetor", "num_operacional", "idtb_turnos", "data_blitz", "nom_fant",
                                       "unidade"])

            # Convertendo a coluna data_blitz para datetime
            df['data_blitz'] = pd.to_datetime(df['data_blitz'])

            # Filtros na barra lateral
            st.sidebar.header("Filtros")
            ano_selecionado = st.sidebar.selectbox("Ano", df['data_blitz'].dt.year.unique(), index=0)
            mes_selecionado = st.sidebar.selectbox("Mês", df[df['data_blitz'].dt.year == ano_selecionado][
                'data_blitz'].dt.month.unique(), index=0)
            empresas_unicas = df['nom_fant'].unique()
            empresa_selecionada = st.sidebar.selectbox("Selecione a Empresa", empresas_unicas, index=0)
            unidades_unicas = df[df['nom_fant'] == empresa_selecionada]['unidade'].unique()
            unidade_selecionada = st.sidebar.selectbox("Selecione a Unidade", unidades_unicas, index=0)
            grafico_selecionado = st.sidebar.selectbox("Selecione o Gráfico", ["Quantidade de Blitz por Instrutor",
                                                                               "Quantidade de Inspeção por Equipe",
                                                                               "Taxa de Contato",
                                                                               "Não Conformidades Apontadas",
                                                                               "Não Conformidades por Inspetor"])
            instrutores_unicos = df[(df['nom_fant'] == empresa_selecionada) & (df['unidade'] == unidade_selecionada)][
                'nome_inspetor'].unique()
            instrutores_selecionados = st.sidebar.multiselect("Selecione os Instrutores", instrutores_unicos,
                                                              default=instrutores_unicos)

            # Filtrando os dados
            df_filtrado = df[(df['data_blitz'].dt.year == ano_selecionado) &
                             (df['data_blitz'].dt.month == mes_selecionado) &
                             (df['nom_fant'] == empresa_selecionada) &
                             (df['unidade'] == unidade_selecionada) &
                             (df['nome_inspetor'].isin(instrutores_selecionados))]

            # Consulta para pegar os dados de turnos
            query_turnos = f"""
            SELECT t.num_operacional, t.dt_inicio
            FROM view_power_bi_turnos t
            WHERE t.dt_inicio BETWEEN '{ano_selecionado}-{mes_selecionado:02d}-01' AND '{ano_selecionado}-{mes_selecionado:02d}-31'
              AND t.nom_fant = '{empresa_selecionada}'
              AND t.unidade = '{unidade_selecionada}'
            """
            cursor.execute(query_turnos)
            resultados_turnos = cursor.fetchall()
            df_turnos = pd.DataFrame(resultados_turnos, columns=["num_operacional", "dt_inicio"])

            # Consulta para pegar as não conformidades
            query_nao_conformidades = f"""
            SELECT r.idtb_turnos, r.pergunta, r.resposta_txt, r.resposta_int, c.nome_inspetor
            FROM view_power_bi_blitz_respostas r
            JOIN view_power_bi_blitz_contatos c ON r.Key = c.Key
            JOIN view_power_bi_turnos t ON r.idtb_turnos = t.idtb_turnos
            WHERE t.nom_fant = '{empresa_selecionada}'
              AND t.unidade = '{unidade_selecionada}'
            """
            cursor.execute(query_nao_conformidades)
            resultados_nao_conformidades = cursor.fetchall()
            df_nao_conformidades = pd.DataFrame(resultados_nao_conformidades,
                                                columns=["Turnos", "Perguntas", "Respostas", "Resposta_Int",
                                                         "Inspetor"])
            df_nao_conformidades_reprovadas = df_nao_conformidades[df_nao_conformidades['Resposta_Int'] == 2].drop(
                columns=['Resposta_Int'])

            # Cálculos das equipes para gráficos
            equipes_com_turnos = df_turnos['num_operacional'].unique()
            equipes_inspecionadas = df_filtrado['num_operacional'].unique()
            equipes_inspecionadas_no_turno = set(equipes_inspecionadas).intersection(set(equipes_com_turnos))
            equipes_nao_inspecionadas_no_turno = set(equipes_com_turnos).difference(set(equipes_inspecionadas))

            # Exibição do dashboard
            st.title("Dashboard Inspeções Dinâmicas")

            if grafico_selecionado == "Quantidade de Blitz por Instrutor":
                blitz_por_instrutor = df_filtrado.groupby("nome_inspetor").agg(
                    quantidade_blitz=('idtb_turnos', 'nunique')).reset_index()
                fig1, ax1 = plt.subplots(figsize=(12, 8))
                sns.barplot(y='nome_inspetor', x='quantidade_blitz', data=blitz_por_instrutor, palette='viridis',
                            ax=ax1)
                ax1.set_title(f'Quantidade de Blitz por Instrutor - {mes_selecionado}/{ano_selecionado}', fontsize=16,
                              fontweight='bold')
                ax1.set_xlabel('')
                ax1.set_ylabel('')
                for i, v in enumerate(blitz_por_instrutor['quantidade_blitz']):
                    ax1.text(v + 0.1, i, f'{v}', ha='left', va='center', fontsize=12, color="black")
                st.pyplot(fig1)

            elif grafico_selecionado == "Quantidade de Inspeção por Equipe":
                blitz_por_equipe = df_filtrado.groupby("num_operacional").agg(
                    quantidade_inspecao=('idtb_turnos', 'nunique')).reset_index()
                fig2, ax2 = plt.subplots(figsize=(12, 8))
                sns.barplot(y='num_operacional', x='quantidade_inspecao', data=blitz_por_equipe, palette='viridis',
                            ax=ax2)
                ax2.set_title(f'Quantidade de Inspeção por Equipe - {mes_selecionado}/{ano_selecionado}', fontsize=16,
                              fontweight='bold')
                ax2.set_xlabel('')
                ax2.set_ylabel('')
                for i, v in enumerate(blitz_por_equipe['quantidade_inspecao']):
                    ax2.text(v + 0.1, i, f'{v}', ha='left', va='center', fontsize=12, color="black")
                st.pyplot(fig2)

            elif grafico_selecionado == "Taxa de Contato":
                st.subheader(f'Taxa de Contato - {mes_selecionado}/{ano_selecionado}')

                col1, col2 = st.columns(2)

                with col1:
                    st.write(f'**Equipes Inspecionadas ({len(equipes_inspecionadas_no_turno)}):**')
                    st.dataframe(pd.DataFrame(list(equipes_inspecionadas_no_turno), columns=["Equipes Inspecionadas"]))

                with col2:
                    st.write(f'**Equipes Não Inspecionadas ({len(equipes_nao_inspecionadas_no_turno)}):**')
                    st.dataframe(
                        pd.DataFrame(list(equipes_nao_inspecionadas_no_turno), columns=["Equipes Não Inspecionadas"]))

                fig, ax = plt.subplots()
                categorias = ['Inspecionadas', 'Não Inspecionadas']
                tamanhos = [len(equipes_inspecionadas_no_turno), len(equipes_nao_inspecionadas_no_turno)]
                ax.pie(tamanhos, labels=categorias, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("Set2"))
                ax.axis('equal')
                st.pyplot(fig)

            elif grafico_selecionado == "Não Conformidades Apontadas":
                st.write("Não Conformidades Apontadas:")
                st.dataframe(df_nao_conformidades_reprovadas)

            elif grafico_selecionado == "Não Conformidades por Inspetor":
                nao_conformidades_por_inspetor = df_nao_conformidades_reprovadas.groupby("Inspetor").size().reset_index(
                    name='Quantidade')
                nao_conformidades_total = nao_conformidades_por_inspetor['Quantidade'].sum()
                nao_conformidades_por_inspetor = pd.concat([nao_conformidades_por_inspetor, pd.DataFrame(
                    [{'Inspetor': 'Total', 'Quantidade': nao_conformidades_total}])])
                st.dataframe(nao_conformidades_por_inspetor)

    except Error as e:
        st.error(f"Erro ao conectar ao MariaDB: {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
    finally:
        if connection.is_connected():
            connection.close()
            st.write("Conexão ao MariaDB foi encerrada")


# Executando a função
connect_to_mariadb()
