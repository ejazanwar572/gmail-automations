import os
import sys
import json
import subprocess
import time

def run_cmd(cmd):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    return res.returncode == 0

def merge_json():
    db_path = "scraped_jobs.json"
    if not os.path.exists(db_path):
        return
        
    try:
        remote_content = subprocess.check_output(["git", "show", "origin/main:scraped_jobs.json"]).decode("utf-8")
        remote_jobs = json.loads(remote_content)
    except Exception as e:
        print(f"Failed to read remote database: {e}")
        run_cmd(["git", "checkout", "--ours", db_path])
        return

    try:
        run_cmd(["git", "checkout", "--ours", db_path])
        with open(db_path, "r") as f:
            local_jobs = json.load(f)
            
        merged = {j.get("url"): j for j in remote_jobs if j.get("url")}
        for j in local_jobs:
            url = j.get("url")
            if url:
                if url not in merged or j.get("score", 0) > merged[url].get("score", 0):
                    merged[url] = j
                    
        with open(db_path, "w") as f:
            json.dump(list(merged.values()), f, indent=4)
        run_cmd(["git", "add", db_path])
        print("Successfully merged scraped_jobs.json")
    except Exception as e:
        print(f"Error merging scraped_jobs.json: {e}")
        run_cmd(["git", "checkout", "--theirs", db_path])
        run_cmd(["git", "add", db_path])

def merge_markdown():
    report_path = "job_matches_report.md"
    if not os.path.exists(report_path):
        return
        
    try:
        run_cmd(["git", "checkout", "--ours", report_path])
        with open(report_path, "r") as f:
            our_content = f.read()
            
        run_cmd(["git", "checkout", "--theirs", report_path])
        with open(report_path, "r") as f:
            their_content = f.read()
            
        header_end = our_content.find("\n\n")
        our_body = our_content[header_end+2:]
        their_header_end = their_content.find("\n\n")
        their_body = their_content[their_header_end+2:]
        
        new_section_end = our_body.find("\n---")
        if new_section_end != -1:
            new_run_section = our_body[:new_section_end+4] + "\n"
        else:
            new_run_section = ""
            
        header = their_content[:their_header_end+2]
        updated_content = header + new_run_section + their_body
        
        with open(report_path, "w") as f:
            f.write(updated_content)
        run_cmd(["git", "add", report_path])
        print("Successfully merged job_matches_report.md")
    except Exception as e:
        print(f"Error merging job_matches_report.md: {e}")
        run_cmd(["git", "checkout", "--theirs", report_path])
        run_cmd(["git", "add", report_path])

def main():
    run_cmd(["git", "config", "--global", "user.name", "github-actions[bot]"])
    run_cmd(["git", "config", "--global", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
    
    for attempt in range(5):
        print(f"Push attempt {attempt+1}/5...")
        run_cmd(["git", "stash", "--include-untracked"])
        
        pull_ok = run_cmd(["git", "pull", "--rebase", "origin", "main"])
        pop_ok = run_cmd(["git", "stash", "pop"])
        
        if not pop_ok:
            print("Conflict detected during stash pop, running custom merges...")
            merge_json()
            merge_markdown()
            run_cmd(["git", "stash", "drop"])
            
        run_cmd(["git", "add", "scraped_jobs.json"])
        if os.path.exists("job_matches_report.md"):
            run_cmd(["git", "add", "job_matches_report.md"])
            
        res = subprocess.run(["git", "diff", "--quiet", "--cached"])
        if res.returncode != 0:
            commit_ok = run_cmd(["git", "commit", "-m", "Automated update: scraped jobs and match report [skip ci]"])
            if commit_ok:
                push_ok = run_cmd(["git", "push", "origin", "main"])
                if push_ok:
                    print("Push successful!")
                    return
        else:
            print("No changes to commit")
            return
            
        time.sleep(5)
        
    print("Failed to push changes after 5 attempts", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
