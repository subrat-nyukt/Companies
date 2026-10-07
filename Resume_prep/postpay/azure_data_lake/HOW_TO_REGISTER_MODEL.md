# How to Register the Model in Databricks (Final Step)

After running the `TRAIN_WITH_SIGNATURE.py` script:

1.  **Find the Run**:
    *   Look at the **"Experiments"** sidebar (Right side) in your Notebook.
    *   Click on the **LATEST RUN** (the one at the top).

2.  **Verify the Signature**:
    *   In the Run details page, look at the **Artifacts** section (bottom/right).
    *   Click `model/` folder.
    *   You should now see a file called `MLmodel` that contains the "input_example" and "signature". This confirms it's valid.

3.  **Click "Register Model"**:
    *   Top Right corner -> **"Register Model"** button.
    *   **Model Name**: Type `Postpay_Risk_Engine`.
    *   Click **"Create"**.
    *   Important: If it asks for schema, pick `default` or `main`.

4.  **Promote to Production**:
    *   Don't just register it. DEPLOY IT.
    *   Go to **"Models"** (Left Sidebar) -> Click `Postpay_Risk_Engine`.
    *   You will see "Version 1".
    *   Click the **"Stage"** dropdown (Usually says "None").
    *   Select **"Production"**.
    *   Confirm.

Now your model is LIVE and read-only, ready for the API!
