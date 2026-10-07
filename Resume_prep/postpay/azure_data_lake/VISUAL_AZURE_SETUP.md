# Visual Guide: Creating Azure Data Lake Storage Gen2

## Step 1: Fill Out the Basics Tab

![Basics Form](C:/Users/DELL/.gemini/antigravity/brain/81b93888-477b-44c3-954c-c77f39526cdd/azure_storage_basics_form_1771056361619.png)

### What to enter:

1. **Subscription**: Select your active Azure subscription (e.g., "Azure subscription 1")

2. **Resource group**: 
   - Click "Create new"
   - Enter: `rg-postpay-demo`
   - Click OK

3. **Storage account name**: `adlspostpaydev`
   - Must be lowercase
   - No spaces or special characters
   - If taken, try: `adlspostpay2026`

4. **Region**: `UAE North` (or same as your Databricks)

5. **Performance**: Select **Standard** (cheaper, perfect for our use case)

6. **Redundancy**: Select **Locally-redundant storage (LRS)** (cheapest option)

7. Click **"Next: Advanced >"** button

---

## Step 2: Enable Data Lake Gen2 (CRITICAL!)

![Advanced Form](C:/Users/DELL/.gemini/antigravity/brain/81b93888-477b-44c3-954c-c77f39526cdd/azure_storage_advanced_form_1771056398653.png)

### The ONE critical setting:

Look for the section called **"Data Lake Storage Gen2"**

**Enable hierarchical namespace**: Toggle this to **ON** (blue)

⚠️ This is what makes it a Data Lake instead of regular Blob Storage! Without this, Databricks cannot use Delta Lake format.

Once you toggle it ON, click **"Review + create"** at the bottom.

---

## Step 3: Review and Create

Azure will validate your settings (takes 5 seconds).

If everything is green ✅, click the blue **"Create"** button.

Wait 30-60 seconds. You'll see: **"Your deployment is complete"**

---

## Next: Create Containers

After deployment completes:

1. Click **"Go to resource"**
2. Look for **"Containers"** in the left menu (under Data storage)
3. Click **"+ Container"** three times to create:
   - `bronze` (for raw SAP data)
   - `silver` (for cleaned data)
   - `gold` (for business aggregates)

Then you're ready to upload the simulated SAP data!
