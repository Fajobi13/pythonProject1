# Use the official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the app source code
COPY . .

# Expose the Flask app port
EXPOSE 4000

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=4000"]
