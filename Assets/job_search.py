from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib import admin
import os
import time
import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Snapshot, LLMResult, JobListingResult
# Load environment variables
load_dotenv()


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


@tool('job_search_glassdoor', description="Search for jobs on Glassdoor using parameters (location, keyword, country) based on the user's input. Returns a list of job postings with relevant details.")
def job_search_glassdoor(location: str, keyword: str, country: str):
    """
    Search for jobs on Glassdoor using the BrightData API.
    """
    llm_result_id: int
    url = "https://api.brightdata.com/datasets/v3/trigger"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('BRIGHTDATA_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    params = {
        "dataset_id": "gd_l7j0bx501ockwldaqf",
        "include_errors": "true",
        "type": "discover_new",
        "discover_by": "keyword",
        "limit_per_input": "5"
    }
    
    data = [
        {
            "keyword": keyword,
            "location": location,
            "country": country
        }
    ]
    
    try:
        # Trigger the dataset
        response = requests.post(url, headers=headers, params=params, json=data)
        response.raise_for_status()
        
        snapshot_id = response.json()['snapshot_id']
        
        snapshot = Snapshot(
             snapshot_id=snapshot_id,
             ready=False,
             llm_result_id=llm_result_id,
             data={}
        )
        snapshot.save()

        return "Successfully created snapshot"
        # Wait for the snapshot to be ready
        progress_url = f'https://api.brightdata.com/datasets/v3/progress/{snapshot_id}'
        
        while True:
            progress_response = requests.get(progress_url, headers=headers)
            progress_response.raise_for_status()
            status_data = progress_response.json()
            
            if status_data.get('status') == 'ready':
                break
            time.sleep(5)
        
        # Get the snapshot data
        snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
        snapshot_response = requests.get(snapshot_url, headers=headers)
        snapshot_response.raise_for_status()
        
        return snapshot_response.json()
        
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except KeyError as e:
        return {"error": f"Unexpected API response format: {str(e)}"}

@tool('set_results_title', description="Set the title for the LLM result based on the user's input.")
def set_results_title(llm_result_id: int, title: str) -> str:
    llm_result = LLMResult.objects.filter(id=llm_result_id).first()
    llm_result.save[]

    result = search_jobs_with_agent(llm_result_id, prompt)
    context ['result'] = result

    search_jobs_with_agent(llm_result.id: int, prompt: str) -> str:
    """
    Set the title for the LLM result.
    """
    try:
        llm_result = LLMResult.objects.get(id=llm_result_id)
        llm_result.title = title
        llm_result.save()
        return f"Title set to '{title}' for LLM result ID {llm_result_id}"
    except LLMResult.DoesNotExist:
        return f"LLM result with ID {llm_result_id} does not exist."
    except Exception as e:
        return f"Error setting title: {str(e)}"

def search_jobs_with_agent(llm_result_id: int, prompt: str) -> str:
    """
    Use LangChain agent to search for jobs based on user prompt.
    """
    try:
        agent = create_agent(
            model='gpt-4.1-mini',
            tools=[job_search_glassdoor],
        )
        
        response = agent.invoke({
            'message': [
                {'role': 'system', 'content': 'You are a helpful assistant for finding job listings via Glassdoor based on user prompts.'},
                {'role': 'user', 'content': f"The id of the LLM result is: {llm_result_id}, Always use this ID when calling tools User request: {prompt}"}
            ]
        })
        
        # Extract the response content
        if 'message' in response and len(response['message']) > 0:
            return response['message'][-1].get('content', 'No response content available')
        return "No response received from the agent"
        
    except Exception as e:
        return f"Error in agent execution: {str(e)}"

@login_required
def search_job_view(request):
    """
    View for job search functionality.
    """
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        if prompt:
            result = search_jobs_with_agent(prompt)
            return render(request, 'results.html', {'result': result})
        else:
            return render(request, 'search.html', {'error': 'Please provide a search query'})
    else:
        return render(request, 'search.html')
            try:
                llm_result = LLMResult(
                    title = 'New Job Search'
                    prompt = prompt,
                    status = 'pending',
                    owner = request.user
                )
                llm_result.save()
        else:
            pass

     

# Main URL patterns
"""urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', signup, name='signup'),
    path('admin/', admin.site.urls),
    path('auth/', include('accounts.urls')),
    path('search/', search_job_view, name='search'),  # Moved this to the main urlpatterns
]"""

class LLMResult(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=250)
    prompt = models.TextField()
    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default='pending')

    owner = models.ForeignKey('User', on_delete=models.CASCADE, related_name='llm_results')
    pass

class JobListingResult(models.Model):
    title = models.CharField(max_length=1024)
    job_url = models.URLField(max_length=1024)
    job_type = models.CharField(max_length=1024, null=True, blank=True)
    level = models.CharField(max_length=1024, null=True, blank=True)
    summary = models.TextField(max_length=1024, null=True, blank=True)
    salary = models.CharField(max_length=1024, null=True, blank=True)
    posted = models.CharField(max_length=1024, null=True, blank=True)
    applicants = models.IntegerField(null=True, blank=True)

    llm_result = models.ForeignKey('LLMResult', on_delete=models.CASCADE, related_name='job_listings_results') 

class Snapshot(models.Model):
    snapshot_id = models.CharField(max_length=250)
    ready = models.BooleanField()
    data = models.JSONField()

    llm_result = models.ForeignKey('LLMResult', on_delete=models.CASCADE, related_name='snapshots')
def is_ready(snapshot_id: str) -> bool:
    url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    
    headers = {"Authorization": f"Bearer {os.getenv('BRIGHTDATA_API_KEY')}",
        "Content-Type": "application/json"
    }

    return requests.get(url, headers=headers).json()['status'] == 'ready':

def get_snapshot_data(snapshot_id: str) -> dict:
    url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    
    headers = {"Authorization": f"Bearer {os.getenv('BRIGHTDATA_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requets.get(url, headers=headers)
    response.raise_for_status()
    return response.json()