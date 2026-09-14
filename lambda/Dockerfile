# Production Multi-Stage Container Image for AWS Lambda
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Final lean runtime stage
FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

# Copy installed dependencies and application code
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}
COPY app.py ${LAMBDA_TASK_ROOT}/

# Set Lambda execution handler
CMD [ "app.lambda_handler" ]

