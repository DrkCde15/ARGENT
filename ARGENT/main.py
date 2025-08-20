# A.R.G.E.N.T. — Advanced Responsive General-purpose Engineering & Neural Tool

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
from memory import responder_com_gemini, criar_usuario, autenticar_usuario, atualizar_senha_usuario, atualizar_username_usuario, verificar_usuario_existe

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    ascii_banner = pyfiglet.figlet_format("ARGENT-V5")
    print(ascii_banner)

def mostrar_banner_texto():
    ascii_banner2 = pyfiglet.figlet_format("ARGENT - CHAT")
    print(ascii_banner2)

def mostrar_banner_voz():
    ascii_banner3 = pyfiglet.figlet_format("ARGENT - VOZ")
    print(ascii_banner3)

def alterar_senha(username_atual):
    """
    Permite ao usuário alterar sua senha atual
    """
    print("=== ALTERAÇÃO DE SENHA ===")
    
    # Solicitar nova senha
    nova_senha = getpass.getpass("Digite a nova senha: ").strip()
    if len(nova_senha) < 4:
        print("A nova senha deve ter pelo menos 4 caracteres.")
        return False
    
    confirmar_senha = getpass.getpass("Confirme a nova senha: ").strip()
    if nova_senha != confirmar_senha:
        print("As senhas não coincidem.")
        return False
    
    try:
        atualizar_senha_usuario(username_atual, nova_senha)
        print("Senha alterada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao alterar senha: {e}")
        return False

def alterar_username(username_atual):
    """
    Permite ao usuário alterar seu username atual
    """
    print("=== ALTERAÇÃO DE USERNAME ===")
    
    # Verificar senha atual para segurança
    senha_atual = getpass.getpass("Digite sua senha atual para confirmar: ").strip()
    if not autenticar_usuario(username_atual, senha_atual):
        print("Senha incorreta.")
        return None
    
    # Solicitar novo username
    novo_username = input("Digite o novo username: ").strip()
    if len(novo_username) < 3:
        print("O novo username deve ter pelo menos 3 caracteres.")
        return None
    
    # Verificar se o novo username já existe
    if verificar_usuario_existe(novo_username):
        print("Este username já está em uso.")
        return None
    
    # Confirmar alteração
    confirmacao = input(f"Tem certeza que deseja alterar de '{username_atual}' para '{novo_username}'? (s/n): ").strip().lower()
    if confirmacao not in ['s', 'sim', 'y', 'yes']:
        print("Alteração cancelada.")
        return None
    
    try:
        atualizar_username_usuario(username_atual, novo_username)
        print(f"Username alterado com sucesso de '{username_atual}' para '{novo_username}'!")
        return novo_username
    except Exception as e:
        print(f"Erro ao alterar username: {e}")
        return None

def menu_configuracoes_usuario(username_atual):
    """
    Menu principal para configurações de usuário
    """
    while True:
        limpar_tela()
        mostrar_banner()
        print("\n=== CONFIGURAÇÕES DE USUÁRIO ===")
        print(f"Usuário atual: {username_atual}")
        print("1 - Alterar senha")
        print("2 - Alterar username")
        print("3 - Voltar ao menu principal")
        
        escolha = input("Escolha uma opção: ").strip()
        
        if escolha == "1":
            alterar_senha(username_atual)
            input("\nPressione Enter para continuar...")
        elif escolha == "2":
            novo_username = alterar_username(username_atual)
            if novo_username:
                input("\nPressione Enter para continuar...")
                return novo_username
            input("\nPressione Enter para continuar...")
        elif escolha == "3":
            break
        else:
            print("Opção inválida. Tente novamente.")
            time.sleep(1)
    
    return username_atual

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
            comando = input(f"{username}@ARGENT> ").strip()
            cmd_lower = comando.lower()
            if cmd_lower == "sair":
                print("Encerrando ARGENT.")
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
                        falar("Encerrando ARGENT.")
                        self.running = False
                        break

                    resposta = processar_comando(comando, self.username, modo='voz')
                    if resposta:
                        print(f"ARGENT: {resposta}")
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
        limpar_tela()
        mostrar_banner()
        print(f"\n=== MENU PRINCIPAL - Usuário: {username} ===")
        print("1 - Modo voz")
        print("2 - Modo texto")
        print("3 - Configurações de usuário")
        print("sair - Encerrar ARGENT")
        escolha = input("Escolha: ").strip().lower()

        if escolha == "1":
            resultado = modo_voz(username)
            if resultado == "sair":
                break
        elif escolha == "2":
            resultado = modo_texto(username)
            if resultado == "sair":
                break
        elif escolha == "3":
            novo_username = menu_configuracoes_usuario(username)
            if novo_username != username:
                username = novo_username
                print(f"Sessão atualizada para o usuário: {username}")
        elif escolha == "sair":
            falar("Encerrando JARVIS.")
            break
        else:
            print("Opção inválida.")
            time.sleep(1)

if __name__ == "__main__":
    limpar_tela()
    mostrar_banner()
    try:
        main()
    except KeyboardInterrupt:
        print("\nARGENT encerrado pelo usuário.")
    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        sys.exit(0)