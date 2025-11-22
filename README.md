# assistant

## Usage

1. Install the dependencies.
   ```
   pip install -r back/requirements.txt
   ```

2. Create a .env file in the root directory.
   ```
   WORKING_DIR=working directory for the assistant
   OPENAI_API_KEY=your_openai_api_key

   GOOGLE_SEARCH_API_KEY=your_google_search_api_key
   GOOGLE_SEARCH_CX=your_google_search_cx
   ```

3. Run the assistant.
   ```
   python back/src/main.py
   ```

4. Install and run the front-end.
   ```
   cd front
   npm install
   npm run dev
   ```

5. Open the browser and navigate to http://localhost:5173.