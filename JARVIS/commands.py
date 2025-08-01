import json
import os
import re
from tkinter import messagebox, simpledialog
import unicodedata
import subprocess
import requests
import sys
import ctypes
import shutil
from pathlib import Path
import webbrowser
import yt_dlp
from bs4 import BeautifulSoup
import pyautogui
import time
from datetime import datetime
import pandas as pd
import google.generativeai as genai
from PIL import Image
from memory import limpar_memoria_do_usuario, responder_com_gemini
import whatsapp
import fitz
from docx import Document
from pptx import Presentation
import pyttsx3
import threading
from queue import Queue
from typing import Callable
import warnings

warnings.filterwarnings('ignore')
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
# ========== Configurações de voz ==========
class VoiceCommandSystem:
    def __init__(self):
        self.engine = self._init_voice_engine()
        self.command_queue = Queue()
        self.voice_lock = threading.Lock()
        self.is_speaking = False
        self._start_command_processor()

    def _init_voice_engine(self):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 180)
            engine.setProperty('volume', 0.9)
            return engine
        except Exception as e:
            print(f"Voice engine initialization failed: {e}")
            return None

    def _start_command_processor(self):
        def processor():
            while True:
                cmd_func, args, kwargs = self.command_queue.get()
                try:
                    time.sleep(0.3)  # Small delay to ensure voice starts first
                    cmd_func(*args, **kwargs)
                except Exception as e:
                    print(f"Command execution error: {e}")
                finally:
                    self.command_queue.task_done()

        threading.Thread(target=processor, daemon=True).start()

    def speak(self, text: str):
        """Non-blocking speech with queue management"""
        print(f"JARVIS: {text}")
        
        if not self.engine:
            return

        def _speak():
            with self.voice_lock:
                self.is_speaking = True
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"Speech error: {e}")
                finally:
                    self.is_speaking = False

        threading.Thread(target=_speak, daemon=True).start()

    def add_command(self, command_func: Callable, *args, **kwargs):
        """Add command to execution queue"""
        self.command_queue.put((command_func, args, kwargs))

# Global voice system instance
voice_system = VoiceCommandSystem()

def falar(texto: str):
    """Improved speak function that uses the enhanced voice system"""
    voice_system.speak(texto)

#=========== Funções de Permissão ==========

def is_admin():
    """Checa se o script está rodando como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relancar_como_admin():
    """Relança o script atual como administrador"""
    if not is_admin():
        print("Tentando reiniciar como admin...")
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, ' '.join(sys.argv), None, 1
        )
        if ret <= 32:
            print("Falha ao tentar executar como administrador.")
            return False
        print("Script relançado como administrador, finalizando instância atual.")
        sys.exit(0)
    return True

#=========== Chocolatey ==========

def verificar_choco_instalado():
    """Verifica se o Chocolatey está instalado"""
    try:
        resultado = subprocess.run(["choco", "-v"], capture_output=True, text=True)
        if "Chocolatey" in resultado.stdout or resultado.returncode == 0:
            return True
    except FileNotFoundError:
        return False
    return False

def instalar_chocolatey_via_powershell():
    """Instala o Chocolatey via PowerShell, sem pyautogui"""
    print("[*] Instalando Chocolatey via PowerShell...")
    comando = (
        'Set-ExecutionPolicy Bypass -Scope Process -Force; '
        '[System.Net.ServicePointManager]::SecurityProtocol = '
        '[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; '
        'iex ((New-Object System.Net.WebClient).DownloadString("https://chocolatey.org/install.ps1"))'
    )
    processo = subprocess.run(["powershell", "-Command", comando], capture_output=True, text=True)
    if processo.returncode == 0:
        print("[+] Chocolatey instalado com sucesso.")
        return True
    else:
        print("[-] Falha ao instalar Chocolatey.")
        print(processo.stderr)
        return False

def instalar_programa_choco(programa):
    """Instala o programa via Chocolatey no terminal, usando subprocess"""
    comando = f"choco install {programa} -y"
    print(f"[*] Instalando {programa} via Chocolatey...")
    processo = subprocess.run(comando, shell=True)
    if processo.returncode == 0:
        print(f"[+] {programa} instalado com sucesso.")
        return True
    else:
        print(f"[-] Falha ao instalar {programa}.")
        return False

#=========== Função Principal ==========

def instalar_programa_via_cmd_admin(programa=None, username=None):
    """Função principal para instalar programas via choco com privilégios admin"""
    if not programa:
        return "Nenhum programa informado para instalação."

    if not relancar_como_admin():
        return "Erro ao tentar elevar privilégios."

    if not verificar_choco_instalado():
        print("[*] Chocolatey não encontrado, instalando...")
        sucesso = instalar_chocolatey_via_powershell()
        if not sucesso:
            return "Falha ao instalar Chocolatey, abortando."

        time.sleep(5)  # Dá um tempo para o sistema registrar a instalação

    sucesso = instalar_programa_choco(programa)
    if sucesso:
        return f"Programa {programa} instalado com sucesso."
    else:
        return f"Falha ao instalar o programa {programa}."

#=========== Desinstalação de Programa ==========
def desinstalar_programa(nome_programa, username, modo='texto'):
    try:
        resposta = f"[*] Desinstalando {nome_programa} via Chocolatey..."
        if modo == 'voz':
            falar(resposta)
        print(resposta)

        comando = f'choco uninstall {nome_programa} -y'
        subprocess.run(comando, shell=True)
        return f"{nome_programa} desinstalado com sucesso (ou já não estava instalado)."
    except Exception as e:
        return f"Erro ao desinstalar {nome_programa}: {e}"

# ========== Info Sites ==========
def raspar_site(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "header", "footer", "nav", "form", "aside"]):
            tag.decompose()

        texto = soup.get_text(separator="\n")
        linhas = [linha.strip() for linha in texto.splitlines()]
        texto_limpo = "\n".join([linha for linha in linhas if linha])

        texto_final = texto_limpo[:1500] + ("\n..." if len(texto_limpo) > 1500 else "")

        return texto_final

    except Exception as e:
        return f"Erro ao raspar site: {e}"

def analisar_site(url, username=None):
    texto_limpo = raspar_site(url)  # ou sua função que pega o texto do site
    if texto_limpo.startswith("Erro"):
        return texto_limpo

    prompt = (
        f"Analise e resuma o conteúdo do site abaixo:\n\n{texto_limpo}\n\n"
        "Forneça um resumo objetivo destacando pontos importantes."
    )

    responder_com_gemini([prompt], username)
    resposta = responder_com_gemini([prompt], username)
    return resposta.content

# ========== Baixar Video ==========
def converter_audio_para_aac(caminho_video: Path):
    caminho_saida = caminho_video.with_name(caminho_video.stem + '_aac.mp4')
    cmd = [
        'ffmpeg',
        '-i', str(caminho_video),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-y',  # sobrescreve se existir
        str(caminho_saida)
    ]
    processo = subprocess.run(cmd, capture_output=True, text=True)
    if processo.returncode != 0:
        raise RuntimeError(f'Erro ffmpeg: {processo.stderr}')
    return caminho_saida
def baixar_video_youtube(url, username, modo='texto'):
    try:
        destino = Path.home() / "Documents" / "Vídeos Download"
        destino.mkdir(parents=True, exist_ok=True)

        opcoes = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': str(destino / '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4'
        }

        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
            titulo = info.get('title', 'Vídeo')

        arquivo_baixado = destino / f"{titulo}.mp4"

        # Converter o áudio para AAC para evitar problemas de compatibilidade
        arquivo_corrigido = converter_audio_para_aac(arquivo_baixado)

        # Substitui o arquivo original pelo convertido
        arquivo_baixado.unlink()  # apaga original
        arquivo_corrigido.rename(arquivo_baixado)  # renomeia para original

        msg = f"Vídeo '{titulo}' baixado e convertido com áudio AAC com sucesso em {destino}."

        if modo == 'voz':
            falar(msg)
        return msg

    except Exception as e:
        erro = f"Erro ao baixar vídeo: {str(e)}"
        if modo == 'voz':
            falar(erro)
        return erro

# ========== Baixar Audio ==========
def limpar_nome_arquivo(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode()
    nome = re.sub(r'[^\w.-]', '_', nome)
    return nome

def converter_para_mp3(caminho_arquivo: Path):
    # Sanitize filename antes de converter
    pasta = caminho_arquivo.parent
    nome_limpo = limpar_nome_arquivo(caminho_arquivo.name)
    caminho_limpo = pasta / nome_limpo

    if caminho_arquivo != caminho_limpo:
        caminho_arquivo.rename(caminho_limpo)
        caminho_arquivo = caminho_limpo

    caminho_saida = caminho_arquivo.with_suffix('.mp3')
    cmd = [
        'ffmpeg',
        '-i', str(caminho_arquivo),
        '-vn',
        '-ar', '44100',
        '-ac', '2',
        '-b:a', '192k',
        '-y',
        str(caminho_saida)
    ]
    processo = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if processo.returncode != 0:
        raise RuntimeError(f'Erro ao converter para MP3: {processo.stderr}')
    return caminho_saida
def baixar_audio_youtube(url, username, modo='texto'):
    try:
        destino = Path.home() / "Documents" / "Áudios Download"
        destino.mkdir(parents=True, exist_ok=True)

        opcoes = {
            'format': 'bestaudio/best',
            'outtmpl': str(destino / '%(title)s.%(ext)s'),
            # removi o postprocessor do yt_dlp pra fazer a conversão na mão
            'postprocessors': []
        }

        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
            titulo = info.get('title', 'Áudio')

        # O arquivo baixado pode ter extensão variável, pega a extensão original
        ext = info.get('ext', 'webm')  
        arquivo_baixado = destino / f"{titulo}.{ext}"

        # Converte para mp3 com ffmpeg para garantir compatibilidade
        arquivo_convertido = converter_para_mp3(arquivo_baixado)

        # Apaga o arquivo original e deixa só o mp3
        arquivo_baixado.unlink()

        msg = f"Áudio '{titulo}' baixado e convertido para MP3 com sucesso em {destino}."

        if modo == 'voz':
            falar(msg)
        return msg

    except Exception as e:
        erro = f"Erro ao baixar áudio: {str(e)}"
        if modo == 'voz':
            falar(erro)
        return erro

# ========== Gravação de Tela ==========
def iniciar_gravacao_sistema(username=None):
    try:
        # Inicia a gravação com atalho da Xbox Game Bar
        pyautogui.hotkey('winleft', 'shift', 'r')
        time.sleep(1)

        # Pega o tamanho da tela
        largura, altura = pyautogui.size()

        # Define o arraste da tela (simula área a ser gravada, opcionalmente)
        x_inicial, y_inicial = 10, 10
        x_final, y_final = largura - 10, altura - 10

        pyautogui.moveTo(x_inicial, y_inicial, duration=0.5)
        pyautogui.mouseDown()
        pyautogui.moveTo(x_final, y_final, duration=1)
        pyautogui.mouseUp()
        time.sleep(0.5)
        
        time.sleep(1)  # Dá tempo da Game Bar carregar
        pyautogui.moveTo(879, 44, duration=0.5)
        pyautogui.mouseDown()
        time.sleep(0.1)
        pyautogui.mouseUp()

        return "Gravação iniciada."
    except Exception as e:
        return f"Erro ao iniciar gravação: {str(e)}"

def parar_gravacao_sistema(username=None):
    try:
        # Clica no botão de parar (posição aproximada para Full HD)
        pyautogui.click(879,44, duration=0.5)  # Ajuste se necessário
        time.sleep(1)

        return "Gravação parada."
    except Exception as e:
        return f"Erro ao parar gravação: {str(e)}"

    
# ========== Funções de imagens ==========
class ImageAnalyser:
    """
    Use essa ferramenta para analisar qualquer tipo de imagem enviada pelo usuário.
    Descreva o conteúdo visual da imagem, objetos, pessoas, textos (se houver), cenários e qualquer informação relevante.
    """

    def __init__(self):
        # Configura o modelo Gemini
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def _run(self, image_path: str, username: str) -> str:
        try:
            if not os.path.exists(image_path):
                return f"Caminho inválido: {image_path}"
            
            # Abre a imagem no formato correto
            image = Image.open(image_path).convert("RGB")

            # Gera resposta com multimodal (texto + imagem)
            response = self.model.generate_content([
                "Descreva com detalhes tudo o que está visível nesta imagem.",
                image
            ])

            resposta_texto = response.text.strip()

            # Log e memória
            from memory import registrar_log
            registrar_log(username, f"Análise de imagem: {image_path}")
            registrar_log(username, f"Resultado: {resposta_texto}")

            return resposta_texto

        except Exception as e:
            return f"Erro ao analisar imagem: {e}"

# Função para processar comando de análise de imagem
def analisar_imagem_comando(caminho, username, modo='texto'):
    if not os.path.exists(caminho):
        return f"Caminho inválido: {caminho}"
    
    analyser = ImageAnalyser()
    resultado = analyser._run(caminho, username)

    if modo == 'voz':
        falar(resultado)
    return resultado

# ========== Variáveis para agenda ==========
AGENDA_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Agenda")
os.makedirs(AGENDA_DIR, exist_ok=True)

estado_insercao_agenda = {
    "aguardando_tarefa": False,
    "aguardando_data": False,
    "aguardando_hora": False,
    "tarefa_temp": "",
    "data_temp": ""
}

# ========== Funções da agenda ==========
def get_agenda_path(username):
    safe_user = re.sub(r'[^a-zA-Z0-9_-]', '', username.lower())
    return os.path.join(AGENDA_DIR, f"agenda_{safe_user}.xlsx")

# Inicializa agenda do usuário se não existir
def inicializar_agenda(username):
    path = get_agenda_path(username)
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["Tarefa", "Data", "Hora", "Status"])
        df.to_excel(path, index=False)

def abrir_agenda(match, username):
    path = get_agenda_path(username)
    inicializar_agenda(username)
    try:
        os.startfile(path)
        return f"Abrindo a agenda de {username} agora, senhor."
    except Exception as e:
        return f"Erro ao abrir agenda: {e}"

def ler_agenda(match, username):
    path = get_agenda_path(username)
    if not os.path.exists(path):
        return f"Não encontrei a agenda de {username}, senhor."
    df = pd.read_excel(path)
    if df.empty:
        return f"A agenda de {username} está vazia, senhor."
    return df.to_string(index=False)

def limpar_agenda(match, username):
    path = get_agenda_path(username)
    if os.path.exists(path):
        df = pd.DataFrame(columns=["Tarefa", "Data", "Hora", "Status"])
        df.to_excel(path, index=False)
        return f"Agenda de {username} limpa com sucesso, senhor."
    return f"Arquivo da agenda de {username} não encontrado, senhor."

def marcar_como_feita(match, username):
    try:
        tarefa_busca = match.group(1).strip().lower()
        path = get_agenda_path(username)
        if not os.path.exists(path):
            return f"Agenda de {username} não encontrada, senhor."
        df = pd.read_excel(path)
        tarefas = df[df["Tarefa"].str.lower().str.contains(tarefa_busca)]
        if len(tarefas) == 0:
            return f"Tarefa contendo '{tarefa_busca}' não encontrada na agenda de {username}, senhor."
        elif len(tarefas) > 1:
            return "Múltiplas tarefas encontradas. Seja mais específico, senhor."
        else:
            idx = tarefas.index[0]
            df.at[idx, "Status"] = "Concluído"
            df.to_excel(path, index=False)
            return f"Tarefa '{df.at[idx, 'Tarefa']}' marcada como concluída na agenda de {username}, senhor."
    except Exception as e:
        return f"Erro ao marcar tarefa: {str(e)}"

def adicionar_tarefa_completa(match, username):
    try:
        tarefa = match.group(2).strip()
        data = match.group(3) if match.group(3) else datetime.now().strftime("%d/%m/%Y")
        hora = match.group(4) if match.group(4) else ""
        datetime.strptime(data, "%d/%m/%Y")  # valida data
        if hora and not re.match(r'^\d{2}:\d{2}$', hora):
            return "Formato de horário inválido. Use HH:MM."
        path = get_agenda_path(username)
        nova_entrada = {
            "Tarefa": tarefa,
            "Data": data,
            "Hora": hora,
            "Status": "Pendente"
        }
        if os.path.exists(path):
            df = pd.read_excel(path)
            df = pd.concat([df, pd.DataFrame([nova_entrada])], ignore_index=True)
        else:
            df = pd.DataFrame([nova_entrada])
        df.to_excel(path, index=False)
        return f"Tarefa adicionada: '{tarefa}' para {data}{f' às {hora}' if hora else ''} na agenda de {username}."
    except ValueError:
        return "Formato de data inválido. Use DD/MM/AAAA."
    except Exception as e:
        return f"Erro: {str(e)}"

def salvar_tarefa_na_agenda(tarefa, data, hora, username, status="Pendente"):
    path = get_agenda_path(username)
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["Tarefa", "Data", "Hora", "Status"])
    else:
        df = pd.read_excel(path)
    nova_entrada = pd.DataFrame([{
        "Tarefa": tarefa,
        "Data": data,
        "Hora": hora,
        "Status": status
    }])
    df = pd.concat([df, nova_entrada], ignore_index=True)
    df.to_excel(path, index=False)

def checar_tarefas_atrasadas(username):
    path = get_agenda_path(username)
    if not os.path.exists(path):
        return

    try:
        df = pd.read_excel(path, engine='openpyxl')
    except Exception as e:
        print(f"Erro ao abrir o arquivo de tarefas: {e}")
        return

    # Remover caracteres problemáticos que possam causar erros de codificação
    df["Tarefa"] = df["Tarefa"].astype(str).apply(
        lambda x: x.encode('latin1', errors='ignore').decode('latin1'))

    agora = datetime.now()
    tarefas_atrasadas = []

    for idx, row in df.iterrows():
        if row["Status"] != "Concluído" and pd.notna(row["Data"]):
            try:
                data_str = f"{row['Data']} {row['Hora'] if pd.notna(row['Hora']) else '00:00'}"
                data_tarefa = datetime.strptime(data_str, "%d/%m/%Y %H:%M")
                if data_tarefa < agora:
                    tarefas_atrasadas.append((idx, row["Tarefa"]))
            except Exception:
                continue

    if tarefas_atrasadas:
        for idx, tarefa in tarefas_atrasadas:
            opcao = messagebox.askquestion(
                "Tarefa atrasada",
                f"'{tarefa}' está atrasada. Marcar como concluída?",
                icon='warning'
            )
            if opcao == 'yes':
                df.at[idx, "Status"] = "Concluído"
            else:
                nova_data = simpledialog.askstring("Remarcar tarefa", f"Nova data para '{tarefa}' (DD/MM/AAAA):")
                nova_hora = simpledialog.askstring("Remarcar tarefa", f"Nova hora para '{tarefa}' (HH:MM):")
                if nova_data:
                    df.at[idx, "Data"] = nova_data
                if nova_hora:
                    df.at[idx, "Hora"] = nova_hora
        df.to_excel(path, index=False)

def iniciar_insercao_agenda(username):
    estado_insercao_agenda[username] = {
        "aguardando_tarefa": True,
        "aguardando_data": False,
        "aguardando_hora": False,
        "tarefa_temp": "",
        "data_temp": ""
    }
    return "Qual tarefa gostaria de adicionar, senhor?"

def processar_resposta_insercao(comando, username):
    estado = estado_insercao_agenda.get(username)
    if not estado:
        return "Nenhuma inserção em andamento, senhor."

    if estado["aguardando_tarefa"]:
        estado["tarefa_temp"] = comando
        estado["aguardando_tarefa"] = False
        estado["aguardando_data"] = True
        return "Qual a data da tarefa (formato DD/MM/AAAA), senhor?"
    elif estado["aguardando_data"]:
        estado["data_temp"] = comando
        estado["aguardando_data"] = False
        estado["aguardando_hora"] = True
        return "Qual o horário da tarefa (ex: 14:00), senhor?"
    elif estado["aguardando_hora"]:
        tarefa = estado["tarefa_temp"]
        data = estado["data_temp"]
        hora = comando
        salvar_tarefa_na_agenda(tarefa, data, hora, username)
        estado["aguardando_hora"] = False
        estado["tarefa_temp"] = ""
        estado["data_temp"] = ""
        del estado_insercao_agenda[username]
        return f"Tarefa '{tarefa}' adicionada para o dia {data} às {hora}, senhor."

# ========== Abrir aplicativos ==========
def abrir_aplicativo(match, username):
    nome = match.group(2).lower()
    try:
        with open('./config/aplicativos.json', 'r', encoding='utf-8') as f:
            apps = json.load(f)
    except Exception as e:
        return f"Erro ao carregar lista de aplicativos: {e}"

    for chave in apps:
        if nome in chave.lower() or chave.lower() in nome:
            try:
                os.system(apps[chave])
                return f"Abrindo {chave}, senhor."
            except Exception as e:
                return f"Erro ao abrir aplicativo {chave}: {e}"
    return f"Aplicativo '{nome}' não encontrado, senhor."

# ========== Abrir sites ==========
def abrir_site(match, username):
    comando = match.group(0).lower()
    sites = {
        "github": "https://github.com/DrkCde15",
        "netflix": "https://www.netflix.com/browse",
        "youtube": "https://youtube.com",
        "microsoft teams": "https://teams.microsoft.com/v2/",
        "instagram": "https://www.instagram.com/jc_v05/",
        "whatsapp": "https://web.whatsapp.com/",
        "tik tok": "https://www.tiktok.com/@bx_329",
        "e-mail": "https://mail.google.com/mail/u/1/#inbox",
    }
    for nome, url in sites.items():
        if nome in comando:
            try:
                webbrowser.open(url)
                return f"Abrindo {nome}, senhor."
            except Exception as e:
                return f"Erro ao abrir site {nome}: {e}"
    return "Site não reconhecido, senhor."

# ======= Atualizações e limpeza =======

def verificar_atualizacoes(match, username):
    try:
        subprocess.run("powershell -Command \"Get-WindowsUpdate\"", shell=True)
        return "Verificando atualizações do sistema, senhor."
    except Exception as e:
        return f"Erro ao verificar atualizações: {e}"

def atualizar_sistema(match, username):
    try:
        subprocess.run("powershell -Command \"Install-WindowsUpdate -AcceptAll -AutoReboot\"", shell=True)
        return "Atualizações sendo instaladas, senhor. O sistema pode reiniciar automaticamente."
    except Exception as e:
        return f"Erro ao atualizar sistema: {e}"

def limpar_lixo(match, username):
    try:
        pastas = [
            os.getenv('TEMP'),
            os.path.join(os.getenv('SystemRoot'), 'Temp')
        ]
        for pasta in pastas:
            for arquivo in os.listdir(pasta):
                caminho = os.path.join(pasta, arquivo)
                try:
                    if os.path.isfile(caminho) or os.path.islink(caminho):
                        os.unlink(caminho)
                    elif os.path.isdir(caminho):
                        shutil.rmtree(caminho)
                except Exception:
                    pass
        return "Arquivos temporários e lixo digital limpos com sucesso, senhor."
    except Exception as e:
        return f"Erro ao limpar arquivos: {e}"

# ======= YouTube e Spotify =======

def tocar_musica(match, username):
    try:
        musica = input("Qual música deseja ouvir, senhor?\n>> ").strip()
        if not musica:
            return "Nenhuma música informada, senhor."
        query = musica.replace(" ", "+")
        url = f"https://www.youtube.com/results?search_query={query}"
        webbrowser.open(url)
        return f"Buscando '{musica}' no YouTube agora, senhor."
    except Exception as e:
        return f"Erro ao abrir o YouTube: {e}"

def tocar_musica_spotify(match, username):
    try:
        musica = input("Qual música deseja ouvir no Spotify, senhor?\n>> ").strip()
        if not musica:
            return "Nenhuma música informada, senhor."
        query = musica.replace(" ", "%20")
        url = f"https://open.spotify.com/search/{query}"
        webbrowser.open(url)
        return f"Buscando '{musica}' no Spotify agora, senhor. Faça login para ouvir."
    except Exception as e:
        return f"Erro ao abrir o Spotify: {e}"
# ========== Funções de data e hora ==========
def falar_hora(match, username):
    return f"Agora são {datetime.now().strftime('%H:%M')}"

def falar_data(match, username):
    return f"Hoje é dia {datetime.now().strftime('%d/%m/%Y')}"

# ========== Funções de pastas ==========
def encontrar_pasta(nome_pasta_usuario):
    home = os.path.expanduser("~")
    mapeamento = {
        "documentos": "Documents",
        "downloads": "Downloads",
        "imagens": "Pictures",
        "desktop": "Desktop",
        "musicas": "Music",
        "videos": "Videos"
    }
    nome_sistema = mapeamento.get(nome_pasta_usuario.lower(), nome_pasta_usuario)
    caminho = os.path.join(home, nome_sistema)
    if os.path.exists(caminho):
        return caminho
    for item in os.listdir(home):
        if nome_pasta_usuario.lower() in item.lower():
            caminho_tentativa = os.path.join(home, item)
            if os.path.isdir(caminho_tentativa):
                return caminho_tentativa
    return None

def abrir_pasta(match, username):
    nome_pasta_usuario = match.group(1).strip()
    caminho = encontrar_pasta(nome_pasta_usuario)
    if caminho:
        try:
            comando = f"Start-Process explorer -ArgumentList '{caminho}' -WindowStyle Maximized"
            subprocess.run(["powershell", "-Command", comando], check=True)
            return f"Abrindo a pasta {os.path.basename(caminho)}, senhor."
        except Exception as e:
            return f"Erro ao abrir a pasta: {e}"
    return f"Pasta '{nome_pasta_usuario}' não encontrada, senhor."

# ========== Listagem ==========
def listar_aplicativos(match, username):
    try:
        with open('./config/aplicativos.json', 'r', encoding='utf-8') as f:
            apps = json.load(f)
    except Exception as e:
        return f"Erro ao carregar lista de aplicativos: {e}"
    return "Aplicativos disponíveis:\n" + "\n".join(f"- {k}" for k in apps.keys())

def listar_sites(match, username):
    try:
        with open('./config/sites.json', 'r', encoding='utf-8') as f:
            sites = json.load(f)
    except Exception as e:
        return f"Erro ao carregar lista de sites: {e}"
    return "Sites disponíveis:\n" + "\n".join(f"- {k}" for k in sites.keys())

# ========== Pesquisa Google ==========
def pesquisar_google(match, username):
    """Executa pesquisa no Google"""
    try:
        # Extrai o termo de pesquisa do grupo correto
        termo = match.group(2).strip()  # Grupo 2 contém o termo de pesquisa
        
        if not termo:
            return "Por favor especifique o que deseja pesquisar, Senhor."

        url = f"https://www.google.com/search?q={termo.replace(' ', '+')}"
        webbrowser.open_new(url)
        return f"Mostrando resultados para '{termo}', Senhor."
    
    except Exception as e:
        return f"Erro ao pesquisar: {str(e)}"

# ========== Criação e manipulação de arquivos ==========
def criar_arquivo(match, username):
    documentos = Path.home() / "Documents"
    nome = input("Digite o nome do arquivo (ex: texto.txt): ").strip()
    if not nome:
        falar("Nome de arquivo inválido.")
        return "Operação cancelada."
    conteudo = input("Digite o conteúdo que deseja salvar: ")
    caminho_completo = documentos / nome
    try:
        with open(caminho_completo, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return f"Arquivo '{nome}' criado com sucesso na pasta Documentos."
    except Exception as e:
        return f"Erro ao criar o arquivo: {e}"

def criar_codigo(match, username):
    documentos = Path.home() / "Documents"
    documentos.mkdir(exist_ok=True)
    linguagem = input("Qual linguagem de programação você quer usar? ").strip().lower()
    descricao = input("Descreva o que o código deve fazer: ").strip()
    prompt = f"Crie um código em {linguagem} que: {descricao}"
    try:
        codigo = responder_com_gemini(prompt, username)
    except Exception as e:
        return f"Erro ao gerar código com Gemini: {e}"
    extensoes = {
        "python": ".py",
        "javascript": ".js",
        "java": ".java",
        "html": ".html",
        "c": ".c",
        "cpp": ".cpp",
        "go": ".go",
        "php": ".php"
    }
    ext = extensoes.get(linguagem, ".txt")
    nome_arquivo = input("Nome do arquivo (sem extensão)? ").strip() + ext
    caminho = documentos / nome_arquivo
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(codigo)
        return f"Código gerado e salvo em: {caminho}"
    except Exception as e:
        return f"Erro ao salvar o arquivo: {e}"

def listar_arquivos(match, username):
    extensao = (match.group(1) or "").lower().replace(".", "").strip()
    pasta = (match.group(2) or "Documentos").lower().strip()
    base_path = Path.home()
    nome_pasta = {
        "documentos": "Documents",
        "documents": "Documents",
        "area de trabalho": "Desktop",
        "área de trabalho": "Desktop",
        "desktop": "Desktop",
        "downloads": "Downloads"
    }.get(pasta, pasta)
    diretorio = base_path / nome_pasta
    if not diretorio.exists():
        return f"A pasta '{nome_pasta}' não foi encontrada, senhor."
    try:
        arquivos = list(diretorio.rglob(f"*.{extensao}")) if extensao else list(diretorio.rglob("*"))
        if not arquivos:
            if extensao:
                return f"Senhor, não encontrei arquivos '.{extensao}' na pasta '{nome_pasta}'."
            return f"Senhor, a pasta '{nome_pasta}' está vazia."
        lista = "\n- " + "\n- ".join([str(arq.relative_to(base_path)) for arq in arquivos])
        if extensao:
            return f"Senhor, encontrei os seguintes arquivos '.{extensao}' na pasta '{nome_pasta}' e suas subpastas:\n{lista}"
        return f"Senhor, encontrei os seguintes arquivos na pasta '{nome_pasta}' e suas subpastas:\n{lista}"
    except Exception as e:
        return f"Erro ao listar arquivos: {e}"

# ========== Funções para ler arquivos ==========
def buscar_arquivo_por_nome(nome_arquivo, pasta_base=None):
    if pasta_base is None:
        pasta_base = Path.home() / "Documents"
    for arquivo in pasta_base.rglob("*"):
        if arquivo.name.lower() == nome_arquivo.lower():
            return arquivo.resolve()
    return None

def ler_docx(caminho):
    try:
        doc = Document(caminho)
        return '\n'.join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"Erro ao ler .docx: {e}"

def ler_txt(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler TXT: {e}"

def ler_csv(caminho):
    try:
        df = pd.read_csv(caminho)
        return df.to_string(index=False)
    except Exception as e:
        return f"Erro ao ler CSV: {e}"

def ler_json(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return f"Erro ao ler JSON: {e}"

def ler_pdf(caminho):
    try:
        doc = fitz.open(caminho)
        return ''.join(pagina.get_text() for pagina in doc)
    except Exception as e:
        return f"Erro ao ler PDF: {e}"

def ler_excel(caminho):
    try:
        df = pd.read_excel(caminho)
        return df.to_string(index=False)
    except Exception as e:
        return f"Erro ao ler Excel: {e}"

def ler_pptx(caminho):
    try:
        prs = Presentation(caminho)
        texto = ''
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texto += shape.text + "\n"
        return texto
    except Exception as e:
        return f"Erro ao ler PPTX: {e}"

def analisar_arquivos(match, username):
    try:
        nome_arquivo = match.group(2).strip()
        arquivo_encontrado = buscar_arquivo_por_nome(nome_arquivo)
        if not arquivo_encontrado:
            return f"Não encontrei o arquivo '{nome_arquivo}' na pasta Documentos, senhor."
        
        sufixo = arquivo_encontrado.suffix.lower()
        conteudo = None

        if sufixo == ".txt":
            conteudo = ler_txt(arquivo_encontrado)
        elif sufixo == ".docx":
            conteudo = ler_docx(arquivo_encontrado)
        elif sufixo == ".csv":
            conteudo = ler_csv(arquivo_encontrado)
        elif sufixo == ".json":
            conteudo = json.dumps(ler_json(arquivo_encontrado), indent=4)
        elif sufixo == ".pdf":
            conteudo = ler_pdf(arquivo_encontrado)
        elif sufixo in [".xlsx", ".xls"]:
            conteudo = ler_excel(arquivo_encontrado)
        elif sufixo == ".pptx":
            conteudo = ler_pptx(arquivo_encontrado)
        else:
            return f"Formato de arquivo '{sufixo}' não suportado, senhor."

        if not conteudo or not conteudo.strip():
            return "O arquivo está vazio ou ilegível, senhor."

        prompt = f"Analise esse conteúdo extraído do arquivo:\n\n{conteudo}"
        resposta = responder_com_gemini(prompt, username)
        return resposta

    except Exception as e:
        return f"Erro ao analisar arquivo: {e}"

# ========== Limpar memória do usuário ==========
def limpar_memoria_do_usuario_command(match, username):
    return limpar_memoria_do_usuario(username)

# ========== Função fallback Gemini ==========
def responder_com_gemini_fallback(match, username):
    comando = match.group(0)
    return responder_com_gemini(comando, username)


# ========== Lista de padrões e ações ==========
padroes = [
    # Abrir o WhatsApp Web
    (re.compile(r'^(executar|iniciar|abrir)whatsapp$', re.IGNORECASE), lambda u, g: whatsapp.iniciar_whatsapp(u)),
    (re.compile(r'^enviar mensagem\s+(.+?)\s+(.+)$', re.IGNORECASE), lambda u, g: whatsapp.enviar_mensagem(u, g.group(1), g.group(2))),
    (re.compile(r'^(listar|mostrar|exibir) contatos$', re.IGNORECASE), lambda u, g: whatsapp.listar_contatos(u)),
    (re.compile(r'^editar contato (\w+) (\w+)$', re.IGNORECASE), lambda u, g: whatsapp.editar_contato(u, g.group(1), g.group(2))),
    (re.compile(r'^apagar contato (\w+)$', re.IGNORECASE), lambda u, g: whatsapp.apagar_contato(u, g.group(1))),
    (re.compile(r'^bloquear contato (\w+)$', re.IGNORECASE), lambda u, g: whatsapp.bloquear_contato_cmd(u, g.group(1))),
    (re.compile(r'^desbloquear contato (\w+)$', re.IGNORECASE), lambda u, g: whatsapp.desbloquear_contato_cmd(u, g.group(1))),

    # Listar aplicativos
    (re.compile(r'\b(listar|mostrar|exibir)\s+(os\s+)?aplicativos\b', re.IGNORECASE), listar_aplicativos),
    
    # Listar sites
    (re.compile(r'\b(listar|mostrar|exibir)\s+(os\s+)?sites\b', re.IGNORECASE), listar_sites),
    
    # Analisar arquivos
    (re.compile(r'\banalisar\s+arquivo\s+(.+)', re.IGNORECASE), lambda m, u: analisar_arquivos(m, u)),
    
    # Analisar site
    (re.compile(r'\banalisar\s+site\s+(.+)', re.IGNORECASE), lambda m, u: analisar_site(m.group(1).strip(), u)),
    
    #Instalar e Desinstalar programas
    (re.compile(r"\b(?:instalar|instale|baixar|baixa|quero instalar)\s+([a-zA-Z0-9\-\.]+)", re.IGNORECASE), 
     lambda m, u: instalar_programa_via_cmd_admin(m.group(1), u)),
    (re.compile(r"\b(?:desinstalar|remover|apagar)\s+([a-zA-Z0-9\-\.]+)", re.IGNORECASE), 
     lambda m, u: desinstalar_programa(m.group(1), u, 'texto')),
    
    # Baixar videos e musicas
    (re.compile(r"\b(baixar|fazer download de|salvar)\b.*?\b(vídeo|video)\b.*?(https?://[^\s]+)", re.IGNORECASE), 
     lambda m, u: baixar_video_youtube(m.group(3), u)),
    (re.compile(r"\b(baixar|fazer download de|salvar)\b.*?\b(áudio|audio|som|mp3|musica|música)\b.*?(https?://[^\s]+)", re.IGNORECASE), 
     lambda m, u: baixar_audio_youtube(m.group(3), u)),
    
    # Gravação de Tela
    (re.compile(r'\b(gravar|iniciar)\s+(?:vídeo|video|gravação|gravacao|tela)\b', re.IGNORECASE), 
     lambda m, u: iniciar_gravacao_sistema()),
    (re.compile(r'\b(parar|finalizar)\s+(?:vídeo|video|gravação|gravacao|tela)\b', re.IGNORECASE), 
     lambda m, u: parar_gravacao_sistema()),
    
    # Abrir sites e aplicativos
    (re.compile(r'\b(iniciar|abrir|executar)\s+(youtube|netflix|microsoft teams|github|instagram|tik\s*tok|e-?mail|email)\b', re.IGNORECASE), 
     abrir_site),
    (re.compile(r'\b(executar|abrir|iniciar)\s+(notepad|google|brave|word|excel|powerpoint|vscode|explorador|prompt|powershell)\b', re.IGNORECASE), 
     abrir_aplicativo),
    
    # Analisar imagens
    (re.compile(r'\banalisar\s+imagem\s+(.+)', re.IGNORECASE), 
     lambda m, u: analisar_imagem_comando(m.group(1).strip(), u)),
    
    # Comandos de sistema
    (re.compile(r'\bverificar\s+atualiza[cç][aã]o(es)?\b', re.IGNORECASE), 
     verificar_atualizacoes),
    (re.compile(r'\batualizar\s+(o\s+)?sistema\b', re.IGNORECASE), 
     atualizar_sistema),
    (re.compile(r'\blimpar\s+(arquivos\s+)?tempor[aá]rios|limpar\s+lixo\b', re.IGNORECASE), 
     limpar_lixo),
    
    # Tocar música YouTube/Spotify
    (re.compile(r'\btocar\s+(m[uú]sica|youtube)\b', re.IGNORECASE), 
     tocar_musica),
    (re.compile(r'\btocar\s+spotify\b', re.IGNORECASE), 
     tocar_musica_spotify),
    
    # Comandos de arquivos
    (re.compile(r'\b(criar|gerar)\s+(arquivo|documento)\b', re.IGNORECASE), 
     criar_arquivo),
    (re.compile(r'\b(criar|fazer|gerar)\s+(código|codigo)\b', re.IGNORECASE), 
     criar_codigo),
    (re.compile(r'\blistar\s+arquivos\s+(?:com\s+(?:a\s+)?extens[aã]o\s+)?(\.?\w+)?(?:\s+na\s+pasta\s+(\w+))?', re.IGNORECASE), 
     listar_arquivos),
    (re.compile(r'\babrir\s+pasta\s+(.+)', re.IGNORECASE), 
     abrir_pasta),
    (re.compile(r'\b(ler|analisar)\s+arquivo\s+(.+)', re.IGNORECASE), 
     analisar_arquivos),
    
    # Comandos de agenda
    (re.compile(r'\bler\s+agenda\b', re.IGNORECASE), 
     ler_agenda),
    (re.compile(r'\babrir\s+agenda\b', re.IGNORECASE), 
     abrir_agenda),
    (re.compile(r'\blimpar\s+agenda\b', re.IGNORECASE), 
     limpar_agenda),
    (re.compile(r'\bmarcar\s+como\s+feita\s+(?:tarefa\s+)?(.+)', re.IGNORECASE), 
     marcar_como_feita),
    (re.compile(r'\b(adicionar|inserir|criar)\s+(.+?)\s+na\s+agenda(?:\s+no\s+dia\s+(\d{2}/\d{2}/\d{4}))?(?:\s+no\s+hor[áa]rio\s+(\d{2}:\d{2}))?', re.IGNORECASE), 
     adicionar_tarefa_completa),
    
    # Comandos data e hora
    (re.compile(r'\bfalar\s+hora\b', re.IGNORECASE),
     falar_hora),
    (re.compile(r'\bfalar\s+data\b', re.IGNORECASE), 
     falar_data),
    
    # Comandos de memória
    (re.compile(r'\blimpar\s+(?:a\s+)?mem[oó]ria\b', re.IGNORECASE), 
     limpar_memoria_do_usuario_command),
    
    # Comandos de pesquisa
    ((re.compile(r'\b(pesquisar|buscar|procurar)\s+(?:por\s+)?(.+)', re.IGNORECASE), pesquisar_google)),
    
    # Comandos de gemini
    (re.compile(r'.+'), 
     responder_com_gemini_fallback)
]

# ========== Enhanced Command Processor ==========
def processar_comando(comando, username, modo='texto'):
    """Processa comandos sem passar o parâmetro 'modo' para as funções"""
    for padrao, acao in padroes:
        match = padrao.search(comando)
        if match:
            try:
                resultado = acao(match, username)  # Remove o parâmetro 'modo'
                
                if modo == 'voz':
                    falar(resultado)
                return resultado
                    
            except Exception as e:
                erro = f"Erro ao processar comando: {e}"
                if modo == 'voz':
                    falar(erro)
                return erro
                
    msg = "Comando não reconhecido, Senhor."
    if modo == 'voz':
        falar(msg)
    return msg