import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from tavily import TavilyClient

# Load environment variables
load_dotenv(dotenv_path=".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

class CompanyResearch:
    def lookup(self):
        Tavily = TavilyClient(api_key=TAVILY_API_KEY)
        query = input("Enter the Company name : ")
        response = Tavily.search(query=query, max_results=10)
        return query, response

    def llm(self, company, search_data):
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a precise corporate data extraction assistant. 
Using ONLY the provided background search results, extract the following information about the company. 
If a specific piece of information is completely missing from the text, write "Not found in search results".

Format your output EXACTLY like this:
Owner Name: [Extract owner, founder, or parent organization]
Company Establishment Date: [Extract founding date or year]
Company Currently Working On: [Summarize current main products, projects, or focus areas]
Company's Required Technologies: [List core technologies, programming languages, framework tools, or tech stacks used]"""),
            ("human", "Company to analyze: {company}\n\nSearch Results:\n{search_data}")
        ])

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            temperature=0.3,
        )

        response = llm.invoke(
            prompt.format(company=company, search_data=search_data)
        )

        print("\n" + "="*40)
        print(f"📊 STRUCTURED PROFILE FOR: {company.upper()}")
        print("="*40)
        print(response.content)
        print("="*40)

if __name__ == "__main__":
    research = CompanyResearch()
    company, search_data = research.lookup()
    research.llm(company, search_data)
