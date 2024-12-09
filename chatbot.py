import customtkinter as ctk
import spacy
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import csv
import unicodedata


class Chatbot:
    def __init__(self, master):
        self.master = master
        master.title("Artemis")
        master.geometry("600x500")

        # Configuração da janela
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=0)
        master.grid_rowconfigure(2, weight=0)

        # Modo e tema de aparência
        ctk.set_appearance_mode("dark")  # "light" ou "dark"

        # Área de texto
        self.text_area = ctk.CTkTextbox(master, width=500, height=300, wrap="word")
        self.text_area.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.text_area.insert(ctk.END, "Olá! Eu sou a Artemis, sua assistente virtual. Como posso te ajudar hoje?\n\n")
        self.text_area.configure(state="disabled", text_color="#00FF00")

        # Entrada de texto
        self.entry = ctk.CTkEntry(master, width=400, placeholder_text="Digite sua pergunta aqui...")
        self.entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.entry.bind("<Return>", self.process_input)

        self.send_button = ctk.CTkButton(master, text="Enviar", fg_color="blue", command=self.process_input)
        self.send_button.grid(row=2, column=0, padx=20, pady=10)

        # Carregar modelo Spacy
        self.nlp = spacy.load("pt_core_news_sm")  # Modelo de PLN em português

        # Variável para armazenar sugestões do contexto atual
        self.suggestions = []

    def process_input(self, event=None):
        user_input = self.entry.get().lower().strip()
        if not user_input:
            return

        self.text_area.configure(state="normal")
        self.text_area.insert(ctk.END, "Você: " + user_input + "\n\n")

        # Respostas personalizadas para interações comuns
        if user_input in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]:
            self.text_area.insert(ctk.END, "Artemis: Olá! Como posso te ajudar hoje?\n\n")
        if user_input in ["obrigado", "obrigada", "valeu", "vlw", "muito obrigado", "muito obrigada"]:
            self.text_area.insert(ctk.END, "Artemis: Fico feliz em ajudar.\n\n")
        elif user_input in ["tchau", "adeus", "até mais", "até logo"]:
            self.text_area.insert(ctk.END, "Artemis: Tchau! Foi um prazer ajudar. Até a próxima!\n\n")
        elif user_input == "clear":
            self.text_area.delete("1.0", ctk.END)
            self.text_area.insert(ctk.END, "Artemis: Tela limpa. Como posso te ajudar?\n\n")
        else:
            # Verificar se a entrada é uma escolha numérica dentro do contexto de sugestões
            if user_input.isdigit() and self.suggestions:
                choice_index = int(user_input) - 1
                if 0 <= choice_index < len(self.suggestions):
                    chosen_concept = self.suggestions[choice_index]
                    self.suggestions = []  # Limpar contexto após escolha
                    data_response = self.fetch_data(chosen_concept, [])
                    if isinstance(data_response, dict) and 'concept_title' in data_response:
                        self.display_response(data_response)
                    else:
                        self.text_area.insert(ctk.END, "Artemis: Não consegui encontrar informações sobre esse conceito.\n\n")
                else:
                    self.text_area.insert(ctk.END, "Artemis: Escolha inválida. Por favor, tente novamente.\n\n")
            else:
                # Processar entrada como texto normal
                self.suggestions = []  # Limpar sugestões ao processar nova entrada
                data_response = self.fetch_data(user_input, [])
                if isinstance(data_response, dict) and "multiple_matches" in data_response:
                    self.suggestions = list(set(data_response["multiple_matches"]))  # Remover duplicatas
                    options = "\n".join([f"{i+1}. {suggestion}" for i, suggestion in enumerate(self.suggestions)])
                    self.text_area.insert(ctk.END, f"Artemis: Você quis dizer:\n{options}\nEscolha uma opção e tente novamente.\n\n")
                elif isinstance(data_response, dict) and 'concept_title' in data_response:
                    self.display_response(data_response)
                else:
                    self.text_area.insert(ctk.END, "Artemis: Não consegui encontrar informações sobre esse conceito.\n\n")

        self.text_area.configure(state="disabled")
        self.entry.delete(0, ctk.END)

    def fetch_data(self, user_input, entities):
        """Busca dados do CSV com base na entrada do usuário e nas entidades extraídas."""
        file_path = './data/fisica.csv'
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # Pula o cabeçalho

                rows = list(reader)
                concepts = [self.normalize_string(row[0]) for row in rows]

                # Buscar correspondência exata
                exact_match = [row for row in rows if self.normalize_string(row[0]) == user_input]
                if exact_match:
                    return self.format_response(exact_match[0])

                # Buscar correspondências aproximadas
                matches = process.extractBests(user_input, concepts, scorer=fuzz.ratio, limit=3, score_cutoff=60)
                if len(matches) == 1:
                    # Correspondência única encontrada
                    for row in rows:
                        if self.normalize_string(row[0]) == matches[0][0]:
                            return self.format_response(row)
                elif len(matches) > 1:
                    # Múltiplas correspondências, oferecer sugestões
                    return {"multiple_matches": [match[0] for match in matches]}

            return None  # Nenhuma correspondência encontrada
        except Exception as e:
            return f"Erro ao buscar dados: {str(e)}"

    def format_response(self, row):
        """Formata uma resposta a partir de uma linha do CSV."""
        return {
            'concept_title': row[0],
            'concept': row[1],
            'formula': row[2],
            'reference': row[3]
        }

    def display_response(self, data_response):
        """Exibe a resposta formatada para o usuário."""
        self.text_area.insert(ctk.END, f"Artemis:\n\n{data_response['concept_title']}\n\n")
        self.text_area.insert(ctk.END, f"{data_response['concept']}\n\n")
        self.text_area.insert(ctk.END, f"--- Fórmula ---\n\n{data_response['formula']}\n\n")
        self.text_area.insert(ctk.END, f"--- Referência ---\n\n{data_response['reference']}\n\n")

    def normalize_string(self, text):
        """Remove acentuação e normaliza a string para comparações mais precisas."""
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()


if __name__ == "__main__":
    root = ctk.CTk()
    chatbot = Chatbot(root)
    root.mainloop()
