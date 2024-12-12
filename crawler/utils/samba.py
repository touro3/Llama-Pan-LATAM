import os
import requests
import yaml
from crewai import Agent, Crew, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, PDFSearchTool
from dotenv import load_dotenv, find_dotenv
from crawler.utils.properties import SAMBA_API_KEY, SERPER_API_KEY


# Helper to load environment variables
def load_env():
    load_dotenv(find_dotenv())


# Load YAML configuration files
def load_yaml_config(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


agents_config = load_yaml_config("crawler/utils/config/agents.yaml")
tasks_config = load_yaml_config("crawler/utils/config/tasks.yaml")


# Initialize SambaNova LLM
class SambaNovaLLM(LLM):
    def __init__(self, api_key, model, stop=None):
        self.api_key = api_key
        self.model = model
        self.stop = stop or []  # Default stop sequence as empty list

    def call(self, messages, **kwargs):
        return sambanova_completion(
            self.model, messages, kwargs.get("temperature", 0.1)
        )


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


LLModel = SambaNovaLLM(api_key=SAMBA_API_KEY, model="Meta-Llama-3.1-8B-Instruct")


# Configure Serper tool
def get_location():
    try:
        response = requests.get("https://ipinfo.io")
        data = response.json()
        return data.get("region", "Unknown"), data.get("country", "Unknown")
    except Exception as e:
        print(f"Error fetching location: {e}")
        return "Unknown", "Unknown"


region, country = get_location()
serper_tool = SerperDevTool(api_key=SERPER_API_KEY, country=country, location=region)


@CrewBase
class CrawlersCrew:
    """Defines the CrawlersCrew agents and tasks"""

    def __init__(self):
        self.agents_config = agents_config
        self.tasks_config = tasks_config

    @agent
    def crawler(self) -> Agent:
        return Agent(
            config=self.agents_config["crawler"],
            tools=[serper_tool],
            verbose=True,
            llm=LLModel,
        )

    @agent
    def rag(self) -> Agent:
        pdf_tool = PDFSearchTool(
            config=dict(
                llm=dict(
                    provider="huggingface",
                    config=dict(model="Meta-Llama-3.1-8B-Instruct", temperature=0.1),
                ),
                embedder=dict(
                    provider="huggingface", config=dict(model="BAAI/bge-small-en-v1.5")
                ),
            )
        )
        return Agent(
            config=self.agents_config["rag"],
            tools=[pdf_tool],
            verbose=True,
            llm=LLModel,
        )

    @agent
    def summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["summarizer"],
            verbose=True,
            llm=LLModel,
        )

    @task
    def crawler_task(self) -> Task:
        return Task(config=self.tasks_config["crawler_task"], verbose=True)

    @task
    def summarizer_task(self) -> Task:
        return Task(config=self.tasks_config["summarizer_task"], verbose=True)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.crawler(), self.rag(), self.summarizer()],
            tasks=[self.crawler_task(), self.summarizer_task()],
            process="sequential",  # or Process.hierarchical if needed
            verbose=True,
        )


def run(topic: str):
    """
    Run the crew with the given topic.
    """
    # Define the input parameters for the crew
    inputs = {"topic": topic, "region": region, "country": country}

    # Initialize and kickoff the crew
    crawlers_crew = CrawlersCrew().crew()
    crawlers_crew.kickoff(inputs=inputs)


if __name__ == "__main__":
    run("Incêndio em Manaus")
