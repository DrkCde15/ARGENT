import os
import logging
import warnings
import time
import hashlib
import uuid
import base64
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Table, MetaData, Text, DateTime, Integer
from sqlalchemy.orm import sessionmaker
import google.generativeai as genai
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage

load_dotenv()
warnings.simplefilter("ignore", DeprecationWarning)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("API KEY do Gemini não encontrada. Verifique seu .env")
genai.configure(api_key=API_KEY)

engine_chat     = create_engine("sqlite:///./data/memoria_jarvis.db")
engine_usuarios = create_engine("sqlite:///./data/usuarios_jarvis.db")
engine_logs     = create_engine("sqlite:///./data/logs_jarvis.db")

metadata_users = MetaData()
metadata_logs = MetaData()

SessionUsers = sessionmaker(bind=engine_usuarios)
SessionLogs  = sessionmaker(bind=engine_logs)

# Tabelas existentes
usuarios = Table(
    "usuarios", metadata_users,
    Column("username", String, primary_key=True),
    Column("senha_hash", String),
)

contatos = Table(
    "contatos", metadata_users,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False),
    Column("nome", String, nullable=False),
    Column("numero", String, nullable=False),
    Column("criado_em", DateTime, default=datetime.utcnow),
)

# Novas tabelas para mensagens e bloqueios
mensagens = Table(
    "mensagens", metadata_users,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False),         # Usuário do sistema (dono do WhatsApp)
    Column("contato_nome", String, nullable=False),
    Column("contato_numero", String, nullable=True),
    Column("direcao", String, nullable=False),          # 'enviado' ou 'recebido'
    Column("texto", Text, nullable=False),
    Column("timestamp", DateTime, default=datetime.utcnow),
)

bloqueados = Table(
    "bloqueados", metadata_users,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False),
    Column("contato_nome", String, nullable=False),
    Column("contato_numero", String, nullable=True),
    Column("bloqueado_em", DateTime, default=datetime.utcnow),
)

metadata_users.create_all(engine_usuarios)

logs = Table(
    "logs", metadata_logs,
    Column("id", String, primary_key=True),
    Column("username", String),
    Column("acao", Text),
    Column("timestamp", DateTime, default=datetime.utcnow),
)

metadata_logs.create_all(engine_logs)

# ---------- Funções básicas ----------

def registrar_log(username, acao):
    session = SessionLogs()
    try:
        session.execute(logs.insert().values(
            id=str(uuid.uuid4()),
            username=username,
            acao=acao,
            timestamp=datetime.utcnow()
        ))
        session.commit()
    finally:
        session.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def criar_usuario(username, senha):
    session = SessionUsers()
    try:
        if session.query(usuarios).filter_by(username=username).first():
            return f"Usuário '{username}' já existe."
        session.execute(usuarios.insert().values(username=username, senha_hash=hash_senha(senha)))
        session.commit()
        registrar_log(username, "Conta criada")
        return f"Usuário '{username}' criado com sucesso."
    finally:
        session.close()

def autenticar_usuario(username, senha):
    session = SessionUsers()
    try:
        user = session.query(usuarios).filter_by(username=username).first()
        if user and user.senha_hash == hash_senha(senha):
            registrar_log(username, "Login bem-sucedido")
            return True
        registrar_log(username, "Tentativa de login falhou")
        return False
    finally:
        session.close()

# ========= MEMÓRIA DO USUÁRIO ========= #

def iniciar_sessao_usuario(username):
    return SQLChatMessageHistory(session_id=username, connection=engine_chat)

def obter_memoria_do_usuario(username):
    chat_history = iniciar_sessao_usuario(username)
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=chat_history,
        return_messages=True
    )

def limpar_memoria_do_usuario(username):
    try:
        chat_history = iniciar_sessao_usuario(username)
        chat_history.clear()
        registrar_log(username, "Memória apagada")
        return f"Memória do usuário '{username}' apagada com sucesso, Senhor."
    except Exception as e:
        registrar_log(username, f"Erro ao apagar memória: {e}")
        return f"Erro ao limpar a memória: {e}"

# ---------- Funções para mensagens e bloqueios ----------

def salvar_mensagem(username, contato_nome, contato_numero, direcao, texto):
    session = SessionUsers()
    try:
        session.execute(mensagens.insert().values(
            username=username,
            contato_nome=contato_nome,
            contato_numero=contato_numero,
            direcao=direcao,
            texto=texto,
            timestamp=datetime.utcnow()
        ))
        session.commit()
        registrar_log(username, f"Mensagem {direcao} para {contato_nome}: {texto[:50]}")
    except Exception as e:
        registrar_log(username, f"Erro ao salvar mensagem: {e}")
    finally:
        session.close()

def listar_mensagens(username, contato_nome=None):
    session = SessionUsers()
    try:
        query = session.query(mensagens).filter(mensagens.c.username == username)
        if contato_nome:
            query = query.filter(mensagens.c.contato_nome == contato_nome)
        resultados = query.order_by(mensagens.c.timestamp.desc()).all()
        return [{
            "contato_nome": m.contato_nome,
            "contato_numero": m.contato_numero,
            "direcao": m.direcao,
            "texto": m.texto,
            "timestamp": m.timestamp.isoformat()
        } for m in resultados]
    finally:
        session.close()

def bloquear_contato(username, contato_nome, contato_numero=None):
    session = SessionUsers()
    try:
        existe = session.query(bloqueados).filter(
            bloqueados.c.username == username,
            bloqueados.c.contato_nome == contato_nome
        ).first()
        if existe:
            return f"Contato '{contato_nome}' já está bloqueado."
        session.execute(bloqueados.insert().values(
            username=username,
            contato_nome=contato_nome,
            contato_numero=contato_numero,
            bloqueado_em=datetime.utcnow()
        ))
        session.commit()
        registrar_log(username, f"Contato bloqueado: {contato_nome}")
        return f"Contato '{contato_nome}' bloqueado com sucesso."
    except Exception as e:
        registrar_log(username, f"Erro ao bloquear contato: {e}")
        return f"Erro ao bloquear contato: {e}"
    finally:
        session.close()

def desbloquear_contato(username, contato_nome):
    session = SessionUsers()
    try:
        deletado = session.execute(
            bloqueados.delete().where(
                (bloqueados.c.username == username) &
                (bloqueados.c.contato_nome == contato_nome)
            )
        )
        session.commit()
        if deletado.rowcount == 0:
            return f"Contato '{contato_nome}' não estava bloqueado."
        registrar_log(username, f"Contato desbloqueado: {contato_nome}")
        return f"Contato '{contato_nome}' desbloqueado com sucesso."
    except Exception as e:
        registrar_log(username, f"Erro ao desbloquear contato: {e}")
        return f"Erro ao desbloquear contato: {e}"
    finally:
        session.close()

# ========= GEMINI ========= #

def responder_com_gemini(input_usuario, username, tentativas=3, espera=10):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        if isinstance(input_usuario, dict) and "image_b64" in input_usuario:
            image_b64 = input_usuario["image_b64"]
            prompt_text = input_usuario.get("text", "Analise a imagem e diga tudo o que vê.")
            response = model.generate_content([
                prompt_text,
                genai.types.Blob(data=base64.b64decode(image_b64), mime_type="image/jpeg")
            ])
            return response.text.strip()
        
        memory = obter_memoria_do_usuario(username)
        mensagens = memory.chat_memory.messages[-8:]
        historico_formatado = "\n".join([
            f"Usuário: {msg.content}" if isinstance(msg, HumanMessage) else f"JARVIS: {msg.content}"
            for msg in mensagens
        ])
        prompt = (
            "Você é o JARVIS, um assistente pessoal inteligente, frio, direto e sempre vai direto ao ponto sem enrolação\n"
            "Responda em português, sempre chamando o usuário de Senhor.\n"
            f"Histórico:\n{historico_formatado}\n"
            f"Usuário: {input_usuario}\n"
            "JARVIS:"
        )
        resposta = model.generate_content(prompt)
        texto_resposta = resposta.text.strip()
        memory.chat_memory.add_user_message(input_usuario)
        memory.chat_memory.add_ai_message(texto_resposta)
        registrar_log(username, f"Pergunta: {input_usuario}")
        registrar_log(username, f"Resposta: {texto_resposta}")
        return texto_resposta

    except Exception as e:
        registrar_log(username, f"Erro Gemini: {e}")
        if "429" in str(e) and tentativas > 0:
            print(f"Cota da API excedida. Tentando novamente em {espera}s...")
            time.sleep(espera)
            return responder_com_gemini(input_usuario, username, tentativas-1, espera*2)
        logging.error(f"Erro Gemini: {e}")
        return f"Erro Gemini: {e}"