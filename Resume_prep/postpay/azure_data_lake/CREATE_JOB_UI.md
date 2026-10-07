# How to Create a Scheduled Job (Azure Databricks UI)

You don't need to write code to schedule a job. You can do it entirely through the UI.

## Step 1: Create the Notebook First
1.  Go to your Workspace.
2.  Create a **New Notebook**.
3.  Name it: `Daily_Risk_Scoring`.
4.  Copy/Paste the code from `BATCH_SCORING.py` into it.

## Step 2: Create the Job (The Scheduler)
1.  Click **"Workflows"** on the left sidebar (Icon looks like a flow chart).
2.  Click the big blue button **"Create Job"**.
3.  **Name the Job**: `Production_Daily_Scoring`.

## Step 3: Configure the Task
A job is made of "Tasks".
1.  **Task Name**: `Score_All_Customers`.
2.  **Type**: Select **Notebook**.
3.  **Source**: Select **Workspace**.
4.  **Path**: Browse and select the `Daily_Risk_Scoring` notebook you just created.
5.  **Cluster**: Select your existing cluster (or a new Job Cluster).
6.  Click **"Create Task"**.

## Step 4: Set the Schedule (The Automation)
1.  On the right side of the Job page, look for **"Trigger"** or **"Schedule"**.
2.  Click **"Add Trigger"**.
3.  **Trigger Type**: "Scheduled".
4.  **Period**: "Day".
5.  **Time**: "02:00" (2 AM).
6.  **Timezone**: Select your timezone (e.g., Asia/Dubai).
7.  Click **"Save"**.

## Step 5: Activate!
Click **"Run Now"** (Top Right) to test it immediately.
If it turns Green, congratulations! Your model will now run every night automatically.
