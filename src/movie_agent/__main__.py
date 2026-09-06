import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("movie_agent.api:create_app", factory=True, host="127.0.0.1",
                port=int(os.environ.get("MOVIE_AGENT_PORT", "4318")), access_log=False)
