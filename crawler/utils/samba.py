import os
import requests
from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

load_dotenv()

SAMBA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def sambanova_completion(model, messages, temperature=0.1):
    url = "https://api.sambanova.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {SAMBA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages, "temperature": temperature}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")


class SambaNovaLLM(LLM):

    stop = None

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def call(self, messages, **kwargs):
        return sambanova_completion(
            self.model, messages, kwargs.get("temperature", 0.1)
        )


LLModel = SambaNovaLLM(api_key=SAMBA_API_KEY, model="Meta-Llama-3.1-8B-Instruct")


# Get the user's region and country
def get_location():
    try:
        response = requests.get("https://ipinfo.io")
        data = response.json()
        return data.get("region", "Unknown"), data.get("country", "Unknown")
    except Exception as e:
        print(f"Error fetching location: {e}")
        return "Unknown", "Unknown"


region, country = get_location()

# Configure the Serper tool
serper_tool = SerperDevTool(
    api_key=str(SERPER_API_KEY), country=str(country), location=str(region)
)


@CrewBase
class CrawlersCrew:
    @agent
    def crawler(self):
        return Agent(
            config=self.agents_config["crawler"],
            tools=[serper_tool],
            verbose=True,
            llm=LLModel,
        )

    @task
    def crawl(self):
        return Task(
            config=self.tasks_config["crawler_task"],
            output_file="results/results.md",
            verbose=True,
        )

    @crew
    def crew(self):
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run():
    inputs = {
        "topic": "Descrição do problema aqui",
        "region": "Região aqui",
        "country": "País aqui",
    }
    crew = CrawlersCrew().crew()
    try:
        result = crew.kickoff(inputs=inputs)  # Captura o resultado completo do agente
        print("Resultado completo do agente:", result)  # Log do resultado completo

        # Extraia a seção Final Answer
        final_answer_marker = "## Final Answer:"
        final_answer_start = result.find(final_answer_marker)
        if final_answer_start != -1:
            final_answer = result[final_answer_start + len(final_answer_marker):].strip()
        else:
            final_answer = "Nenhum resultado gerado pelo agente."

        print("Final Answer extraída:", final_answer)  # Log da Final Answer
        return final_answer  # Retorna a Final Answer diretamente
    except Exception as e:
        print("Erro ao processar a Final Answer:", str(e))
        raise
