import time
import re
import webbrowser
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from memory import (
    salvar_mensagem,
    bloquear_contato,
    desbloquear_contato,
    registrar_log,
    responder_com_gemini, contatos, SessionUsers
)

driver = None

def abrir_whatsapp_web():
    url = "https://web.whatsapp.com"
    webbrowser.open(url)
    return "WhatsApp Web aberto no navegador padrão. Escaneie o QR e use normalmente."

def buscar_contato_elemento(nome):
    global driver
    try:
        caixa_pesquisa = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        caixa_pesquisa.clear()
        caixa_pesquisa.send_keys(nome)
        time.sleep(2)
        contato = driver.find_element(By.XPATH, f'//span[@title="{nome}"]')
        return contato
    except NoSuchElementException:
        return None

def enviar_mensagem(username, contato_nome, mensagem):
    global driver
    if not driver:
        return "WhatsApp não iniciado. Use 'iniciar whatsapp' antes."

    contato = buscar_contato_elemento(contato_nome)
    if not contato:
        return f"Contato '{contato_nome}' não encontrado."

    contato.click()
    time.sleep(1)

    try:
        # Enviar mensagem original
        caixa_msg = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        caixa_msg.click()
        caixa_msg.send_keys(mensagem + Keys.ENTER)
        time.sleep(1)
        salvar_mensagem(username, contato_nome, None, 'enviado', mensagem)
        registrar_log(username, f"Mensagem enviada para {contato_nome}: {mensagem[:50]}")

        # Gerar resposta automática com Gemini
        resposta_gemini = responder_com_gemini(mensagem, username)
        if resposta_gemini:
            # Enviar resposta gerada pelo Gemini
            caixa_msg.click()
            caixa_msg.send_keys(resposta_gemini + Keys.ENTER)
            time.sleep(1)
            salvar_mensagem(username, contato_nome, None, 'recebido', resposta_gemini)
            registrar_log(username, f"Resposta Gemini enviada para {contato_nome}: {resposta_gemini[:50]}")

        return f"Mensagem enviada para '{contato_nome}' e resposta automática enviada pelo Gemini."

    except NoSuchElementException:
        return "Erro: caixa de mensagem não encontrada."

def listar_contatos(username):
    session = SessionUsers()
    try:
        contatos_list = session.query(contatos).filter(contatos.c.username == username).all()
        resultado = [{"nome": c.nome, "numero": c.numero} for c in contatos_list]
        return resultado
    except Exception as e:
        return []
    finally:
        session.close()

def editar_contato(username, nome_antigo, novo_nome):
    session = SessionUsers()
    try:
        contato = session.query(contatos).filter(
            contatos.c.username == username,
            contatos.c.nome == nome_antigo
        ).first()
        if not contato:
            return f"Contato '{nome_antigo}' não encontrado."
        session.execute(
            contatos.update().where(
                (contatos.c.username == username) & 
                (contatos.c.nome == nome_antigo)
            ).values(nome=novo_nome)
        )
        session.commit()
        registrar_log(username, f"Contato '{nome_antigo}' renomeado para '{novo_nome}'")
        return f"Contato '{nome_antigo}' renomeado para '{novo_nome}'."
    except Exception as e:
        return f"Erro ao editar contato: {e}"
    finally:
        session.close()

def apagar_contato(username, nome):
    session = SessionUsers()
    try:
        contato = session.query(contatos).filter(
            contatos.c.username == username,
            contatos.c.nome == nome
        ).first()
        if not contato:
            return f"Contato '{nome}' não encontrado."
        session.execute(
            contatos.delete().where(
                (contatos.c.username == username) & 
                (contatos.c.nome == nome)
            )
        )
        session.commit()
        registrar_log(username, f"Contato '{nome}' apagado")
        return f"Contato '{nome}' apagado."
    except Exception as e:
        return f"Erro ao apagar contato: {e}"
    finally:
        session.close()

def bloquear_contato_cmd(username, contato_nome):
    return bloquear_contato(username, contato_nome)

def desbloquear_contato_cmd(username, contato_nome):
    return desbloquear_contato(username, contato_nome)