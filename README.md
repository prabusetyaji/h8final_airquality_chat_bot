## Getting Started

### Prerequisites

Ensure you have Python installed. It is recommended to use `miniconda` or `conda` for environment management.

### Installation

1.  **Install Miniconda (if not already installed)**

    Download and install Miniconda from the official website: <mcurl name="Miniconda Installer" url="https://docs.conda.io/en/latest/miniconda.html"></mcurl>

2.  **Create a Conda Environment**

    Open your terminal or Anaconda Prompt and create a new environment:

    ```bash
    conda create -n finalchat-env python=3.9
    conda activate finalchat-env
    ```

3.  **Install Requirements**

    Navigate to the project directory and install the necessary packages:

    ```bash
    pip install -r requirements.txt
    ```
    or
     ```bash
    python -m pip install -r requirements.txt
    ```
    

4.  **Run the Streamlit Application**

    ```bash
    streamlit run streamlit_app.py

    The application will open in your web browser.

5. **Put Google API Key & init database**

    ```
    put Google API key from Google AI Studio & init database before starting the convo

6. **Convo could be triggered with asking sleep quality and asking nearby pm2.5**

    ```
    any conversation must be started with something like this:
    -semalam aku tidur dengan rata2 pm2.5 x ug/m3 selama t jam, kira2 kualitas tidurku gimana ya
    -aku tidak ada air quality monitor, bisakah aku tau berapa kualitas udara di daerahku? untuk aku jadikan referensi pm2.5 selama jam tidur

7. **History, Summary & Last Stats**

    ```
    chatbot would store your log file to keep tracking your sleep quality as you
    continue using the chatbot. you can also summarize and see your past sleep experience using prompt
 
8. **streamlit deployment**

    ```
    the chatbot could also accessed through https://airquality-sleep-coach.streamlit.app/

## Code Structure

- sleep_pm25_coach_bot.py: The main Streamlit application file, containing the chatbot UI and logic.
- sleepdb_tools.py: Contains functions for interacting with the sales_data.db database.
- requirements.txt: Lists all Python dependencies required for the project.
- database/sleep_data.db: would store log files for user input for n times
