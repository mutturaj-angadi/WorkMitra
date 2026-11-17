import time
from locust import HttpUser, task, between

class DeskUser(HttpUser):
    wait_time=between(0.5,1.5)

    @task
    def submit_and_wait_for_complete_run(self):
        started=time.perf_counter()
        response=self.client.post("/api/v1/compliance/requests",json={"question":"Synthetic scenario: does gratuity apply after fixed term employment?","domain":"GRATUITY"},name="submit request")
        run_id=response.json().get("run_id") if response.status_code==202 else None
        deadline=time.perf_counter()+40
        error=None if run_id else Exception(f"submission status {response.status_code}")
        last=response
        while run_id and time.perf_counter()<deadline:
            last=self.client.get(f"/api/v1/compliance/runs/{run_id}/status",name="poll run")
            if last.status_code!=200:
                error=Exception(f"status endpoint returned {last.status_code}"); break
            state=last.json()["status"]
            if state in {"COMPLETED","FAILED"}:
                if state!="COMPLETED": error=Exception("run failed")
                break
            time.sleep(0.2)
        else:
            if run_id: error=Exception("run exceeded 40 second test deadline")
        self.environment.events.request.fire(request_type="ASYNC",name="complete run",response_time=(time.perf_counter()-started)*1000,response_length=0,response=last,context={},exception=error)
