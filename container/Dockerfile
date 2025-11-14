# use python
FROM python:3.12-slim 

# set metadata
LABEL maintainer="task-commander"
LABEL description="Custom Docker image for Task: {{task.name}}"

# set working directory
WORKDIR /app
RUN mkdir -p /app/out

# task set-up
{{task.apt_packages}}
{{task.env_vars}}

CMD ["python", "--version"]
