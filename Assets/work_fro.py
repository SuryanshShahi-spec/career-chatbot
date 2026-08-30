from dataclasses import dataclass
from datetime import datetime
import re
from typing import List

@dataclass
class WorkEntry:
    date: datetime
    hours: float
    project: str
    tasks: str

def parse_with_line(line: str) -> WorkEntry:
  # Example format: 2026-09-01 / 4.5 / Project Alpha / ProjectAlpha / Grade review and bug fixes
  pattern = r'^(\d{4}-\d{2}-\d{2})\s*\|\s*([\d.]+)\s*\|\s*([^|]+)\s*\|\s*(.*)$'
  match = re.match(pattern, line.strip())

  if match:
    date_str, hours_str, project, tasks = match.groups()
    return WorkEntry(
      date=datetime.strptime(date_str, "%Y-%m-%d"),
      hours=float(hours_str),
      project=project.strip(),
      tasks=tasks.strip()
    )
  return None

def parse_with_log(file_content: str) -> List[WorkEntry]:
  entries = []
  for line in file_content.splitlines():
    if line.strip() and not line.startswith('#'):
      entry = parse_with_line(line)
      if entry:
        entries.append(entry)
  return entries

if __name__=='__main__':
   log_data = """
   # WFH Log
   2026-09-01 | 8.5 | ProjectAlpha | Initial API design setup
   2026-09-01 | 8.5 | ProjectBeta | Database schema migration
   """

   passed = parse_with_log(log_data)
   for item in passed:
      print(f"Date: {item.date.date()}. Hours: {item.hours}. Project:{item.project}. Tasks: {item.tasks}")
  
  
  