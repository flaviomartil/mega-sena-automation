# Mega-Sena Automation

Automate data fetching, prediction, and result processing for Mega-Sena lottery games. This repository includes scripts to fetch lottery results, predict numbers using LSTM neural networks, and process games with email notifications.

---

## **Features**

- Fetch and save Mega-Sena results in a MySQL database.
- Predict future numbers using historical data and LSTM models.
- Compare played games with official results and send email notifications.

---

## **Setup**

### **Prerequisites**

- Python 3.8+
- Docker & Docker Compose
- Pip (Python package manager)

### **Clone the Repository**

```bash
git clone https://github.com/yourusername/mega-sena-automation.git
cd mega-sena-automation
```

### **Install Dependencies**

Create a virtual environment (optional) and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## **Configuration**

### **Environment Variables**

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DB_HOST=localhost
DB_USER=user
DB_PASSWORD=userpassword
DB_NAME=megasena
DB_PORT=3309

# Email Configuration
EMAIL=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Played Games
JOGOS=13,19,21,30,43,60|08,17,46,53,55,60|05,11,25,43,45,54

# Result Processing
DATA_APURACAO=17/12/2024
```

### **Database Setup with Docker Compose**

The project includes a `docker-compose.yml` file to set up the MySQL database easily.

**File:** `docker-compose.yml`

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:latest
    container_name: mysql_container
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: megasena
      MYSQL_USER: user
      MYSQL_PASSWORD: userpassword
    ports:
      - "3309:3306"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

**Run:**

```bash
docker-compose up -d
```

This command will create a MySQL container with the required configuration. Ensure the `.env` file matches these settings.

---

## **Scripts**

### **1. Fetch Results**

Fetches all Mega-Sena results from the API and stores them in the database.

**File:** `scripts/fetch_results.py`

**Run:**

```bash
python3 scripts/fetch_results.py
```

### **2. Predict Numbers**

Uses historical results to predict the next possible numbers using an LSTM model.

**File:** `scripts/predict_numbers.py`

**Run:**

```bash
python3 scripts/predict_numbers.py
```

### **3. Process Played Games**

Compares played games with official results, saves them in the database, and sends email notifications.

**File:** `scripts/process_games.py`

**Run:**

```bash
python3 scripts/process_games.py
```

---

## **Database Schema**

### **1. Results Table**

```sql
CREATE TABLE resultados (
    concurso INT PRIMARY KEY,
    data DATE,
    numeros VARCHAR(255)
);
```

### **2. Predictions Table**

```sql
CREATE TABLE previsoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_previsao DATETIME,
    numero_previsto INT,
    combinacao_sugerida VARCHAR(255)
);
```

### **3. Played Games Table**

```sql
CREATE TABLE jogos_jogados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numeros_jogados VARCHAR(255) UNIQUE,
    acertos INT,
    data_comparacao DATE
);
```

---

## **Crontab Configuration**

To automate the scripts, add the following lines to your crontab:

```bash
# Fetch results every day at midnight
0 0 * * * /usr/bin/python3 /path/to/scripts/fetch_results.py >> /path/to/logs/fetch_results.log 2>&1

# Process games every hour
0 * * * * /usr/bin/python3 /path/to/scripts/process_games.py >> /path/to/logs/process_games.log 2>&1
```

---

## **Contributing**

Feel free to submit issues or pull requests to improve this project!

---

## **License**

This project is licensed under the MIT License.
