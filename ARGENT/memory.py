import os
import logging
import warnings
import time
import hashlib
import uuid
import base64
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Table, MetaData, Text, DateTime
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

engine_chat     = create_engine("sqlite:///./data/memoria_argent.db")
engine_usuarios = create_engine("sqlite:///./data/usuarios_argent.db")
engine_logs     = create_engine("sqlite:///./data/logs_argent.db")

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

# ========= NOVAS FUNÇÕES DE ALTERAÇÃO ========= #

def verificar_usuario_existe(username):
    """Verifica se um username já existe no sistema"""
    session = SessionUsers()
    try:
        user = session.query(usuarios).filter_by(username=username).first()
        return user is not None
    finally:
        session.close()

def atualizar_senha_usuario(username, nova_senha):
    """Atualiza a senha do usuário no sistema"""
    session = SessionUsers()
    try:
        user = session.query(usuarios).filter_by(username=username).first()
        if not user:
            raise Exception("Usuário não encontrado")
        
        # Atualiza a senha com hash
        session.execute(
            usuarios.update()
            .where(usuarios.c.username == username)
            .values(senha_hash=hash_senha(nova_senha))
        )
        session.commit()
        registrar_log(username, "Senha alterada com sucesso")
        return True
    except Exception as e:
        session.rollback()
        registrar_log(username, f"Erro ao alterar senha: {e}")
        raise Exception(f"Erro ao salvar alterações da senha: {e}")
    finally:
        session.close()

def atualizar_username_usuario(username_antigo, username_novo):
    """Atualiza o username do usuário no sistema"""
    session = SessionUsers()
    try:
        # Verifica se o usuário antigo existe
        user_antigo = session.query(usuarios).filter_by(username=username_antigo).first()
        if not user_antigo:
            raise Exception("Usuário antigo não encontrado")
        
        # Verifica se o novo username já existe
        user_novo = session.query(usuarios).filter_by(username=username_novo).first()
        if user_novo:
            raise Exception("Novo username já existe")
        
        # Salva a senha do usuário antigo
        senha_hash = user_antigo.senha_hash
        
        # Remove o usuário antigo
        session.execute(usuarios.delete().where(usuarios.c.username == username_antigo))
        
        # Cria o usuário com o novo username
        session.execute(usuarios.insert().values(
            username=username_novo,
            senha_hash=senha_hash
        ))
        
        session.commit()
        
        # Migra dados relacionados
        migrar_dados_usuario(username_antigo, username_novo)
        
        # Registra logs
        registrar_log(username_novo, f"Username alterado de '{username_antigo}' para '{username_novo}'")
        registrar_log(username_antigo, f"Username alterado para '{username_novo}' - conta migrada")
        
        return True
        
    except Exception as e:
        session.rollback()
        registrar_log(username_antigo, f"Erro ao alterar username: {e}")
        raise Exception(f"Erro ao salvar alterações do username: {e}")
    finally:
        session.close()

def migrar_dados_usuario(username_antigo, username_novo):
    """
    Migra dados específicos do usuário quando o username é alterado
    Inclui memória de chat e outros dados relacionados
    """
    try:
        # Migra a memória de chat do SQLChatMessageHistory
        migrar_memoria_chat(username_antigo, username_novo)
        
        # Aqui você pode adicionar outras migrações se necessário
        # Exemplo: arquivos específicos, configurações, etc.
        
        print(f"Dados do usuário migrados: {username_antigo} → {username_novo}")
        
    except Exception as e:
        print(f"Aviso: Erro ao migrar alguns dados do usuário: {e}")
        registrar_log(username_novo, f"Erro parcial na migração de dados: {e}")

def migrar_memoria_chat(username_antigo, username_novo):
    """
    Migra o histórico de chat do usuário antigo para o novo username
    """
    try:
        # Obtém a conexão com o banco de chat
        from sqlalchemy import text
        
        with engine_chat.connect() as conn:
            # Verifica se existem mensagens para o usuário antigo
            result = conn.execute(
                text("SELECT COUNT(*) FROM message_store WHERE session_id = :old_session"),
                {"old_session": username_antigo}
            )
            count = result.scalar()
            
            if count > 0:
                # Atualiza o session_id das mensagens
                conn.execute(
                    text("UPDATE message_store SET session_id = :new_session WHERE session_id = :old_session"),
                    {"new_session": username_novo, "old_session": username_antigo}
                )
                conn.commit()
                print(f"Migradas {count} mensagens de chat")
            else:
                print("Nenhuma mensagem de chat para migrar")
                
    except Exception as e:
        print(f"Erro ao migrar memória de chat: {e}")
        # Não levanta exceção para não interromper o processo principal

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
            f"Usuário: {msg.content}" if isinstance(msg, HumanMessage) else f"ARGENT: {msg.content}"
            for msg in mensagens
        ])
        prompt = (
            "Você é o ARGENT, um assistente pessoal altamente inteligente, profissional e da respostas completas \n"
            "Responda em português, sempre chamando o usuário de Senhor.\n"
            f"Histórico:\n{historico_formatado}\n"
            f"Usuário: {input_usuario}\n"
            "ARGENT:"
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