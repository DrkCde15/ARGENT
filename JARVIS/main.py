import os
import sys
import argparse
import getpass
import time
import pyfiglet
import speech_recognition as sr
import threading
from queue import Queue
from commands import processar_comando, falar, checar_tarefas_atrasadas
from memory import responder_com_gemini, criar_usuario, autenticar_usuario

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    ascii_banner = pyfiglet.figlet_format("JARVIS")
    print(ascii_banner)

def mostrar_banner_texto():
    ascii_banner2 = pyfiglet.figlet_format("JARVIS - CHAT")
    print(ascii_banner2)

def mostrar_banner_voz():
    ascii_banner3 = pyfiglet.figlet_format("JARVIS - VOZ")
    print(ascii_banner3)

def autenticar_usuario_interativo():
    limpar_tela()
    mostrar_banner()
    print("=== AUTENTICAÇÃO ===")
    print("1 - Login")
    print("2 - Criar Conta")
    escolha = input("Escolha: ").strip()

    username = input("Usuário: ").strip()
    senha = getpass.getpass("Senha: ").strip()

    if escolha == "1":
        if autenticar_usuario(username, senha):
            limpar_tela()
            mostrar_banner()
            print(f"Bem-vindo(a) de volta, Senhor(a) {username}.")
            return username
        else:
            print("Credenciais inválidas.")
            sys.exit(1)

    elif escolha == "2":
        confirm_senha = getpass.getpass("Confirme a senha: ").strip()
        if senha != confirm_senha:
            print("As senhas digitadas devem ser iguais.")
            sys.exit(1)
        print(criar_usuario(username, senha))
        limpar_tela()
        mostrar_banner()
        return username
    else:
        print("Opção inválida.")
        sys.exit(1)

def modo_texto(username):
    limpar_tela()
    mostrar_banner_texto()
    print("Modo texto ativado. Digite 'sair' para encerrar.")
    while True:
        try:
            comando = input(f"{username}@JARVIS> ").strip()
            cmd_lower = comando.lower()
            if cmd_lower == "sair":
                print("Encerrando JARVIS.")
                return "sair"
            elif cmd_lower in ["cls", "limpar"]:
                limpar_tela()
                mostrar_banner_texto()
                continue
            else:
                resposta = processar_comando(comando, username, modo='texto')
                if resposta:
                    print("JARVIS:", resposta)
                else:
                    resposta_gemini = responder_com_gemini(comando, username)
                    print("JARVIS:", resposta_gemini)
        except KeyboardInterrupt:
            print("\nDigite 'sair' para encerrar ou continue comandando.")
        except Exception as e:
            print(f"Erro: {e}")

class VoiceCommandProcessor:
    def __init__(self, username):
        self.username = username
        self.command_queue = Queue()
        self.running = True
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self._start_processor()

    def _start_processor(self):
        def processor():
            while self.running:
                try:
                    with self.mic as source:
                        print("Ouvindo...")
                        self.recognizer.adjust_for_ambient_noise(source)
                        audio = self.recognizer.listen(source, timeout=5)

                    comando = self.recognizer.recognize_google(audio, language="pt-BR")
                    print(f"Você: {comando}")

                    if comando.lower() == "sair":
                        falar("Encerrando JARVIS.")
                        self.running = False
                        break

                    resposta = processar_comando(comando, self.username, modo='voz')
                    if resposta:
                        print(f"JARVIS: {resposta}")
                        falar(resposta)

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    falar("Não entendi. Repita, por favor.")
                except sr.RequestError:
                    falar("Erro ao conectar ao serviço de voz.")
                except Exception as e:
                    print(f"Erro no processamento: {e}")

        threading.Thread(target=processor, daemon=True).start()

    def stop(self):
        self.running = False

def modo_voz(username):
    limpar_tela()
    mostrar_banner_voz()
    print("Modo voz ativado. Diga 'sair' para encerrar.")

    processor = VoiceCommandProcessor(username)

    try:
        while processor.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        processor.stop()
        falar("Modo voz interrompido.")
    except Exception as e:
        processor.stop()
        print(f"Erro: {e}")

    return "sair" if not processor.running else None

def notificador_background(username, intervalo=10):
    while True:
        try:
            checar_tarefas_atrasadas(username)
            time.sleep(intervalo)
        except Exception as e:
            print(f"Erro no notificador: {e}")
            time.sleep(intervalo)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', type=str, help='Nome do usuário logado')
    args = parser.parse_args()

    if args.user:
        username = args.user
        print(f"[+] Usuário detectado via argumento: {username}")
    else:
        username = autenticar_usuario_interativo()

    notificador_thread = threading.Thread(target=notificador_background, args=(username,), daemon=True)
    notificador_thread.start()

    while True:
        print("\n1 - Modo voz")
        print("2 - Modo texto")
        print("sair - Encerrar JARVIS")
        escolha = input("Escolha: ").strip().lower()

        if escolha == "1":
            resultado = modo_voz(username)
            if resultado == "sair":
                break
        elif escolha == "2":
            resultado = modo_texto(username)
            if resultado == "sair":
                break
        elif escolha == "sair":
            falar("Encerrando JARVIS.")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    limpar_tela()
    mostrar_banner()
    try:
        main()
    except KeyboardInterrupt:
        print("\nJARVIS encerrado pelo usuário.")
    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        sys.exit(0)