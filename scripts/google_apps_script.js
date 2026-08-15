/**
 * Google Apps Script - Real-Time UPI & Expense Ledger Sync
 * 
 * Instructions:
 * 1. Open Google Sheets.
 * 2. Go to Extensions -> Apps Script.
 * 3. Paste this code, save, and rename the project to "Gmail Expense Ledger Sync".
 * 4. Run the `setup` function once to initialize the sheet and labels.
 * 5. Click the Triggers icon (clock) on the left sidebar, add a trigger for `syncExpenses`,
 *    configured as Time-driven -> Minutes timer -> Every 10 or 15 minutes.
 */

const CONFIG = {
  sheetName: "Expenses",
  processedLabel: "ProcessedExpenseLedger"
};

// Setup sheet headers and Gmail Label
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.sheetName);
  
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.sheetName);
  }
  
  // Clear or setup headers if empty
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "Timestamp", 
      "Transaction Date", 
      "Source", 
      "Amount (INR)", 
      "Merchant / Payee", 
      "Account Ref", 
      "Transaction Ref ID", 
      "VPA",
      "Email Message ID"
    ]);
    sheet.getRange(1, 1, 1, 9).setFontWeight("bold").setBackground("#e2e8f0");
  }
  
  // Create Gmail Label if it doesn't exist
  let label = GmailApp.getUserLabelByName(CONFIG.processedLabel);
  if (!label) {
    GmailApp.createLabel(CONFIG.processedLabel);
  }
  
  Logger.log("Setup completed successfully!");
}

// Main function to sync emails
function syncExpenses() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.sheetName);
  if (!sheet) {
    Logger.log("Error: Target sheet 'Expenses' not found. Run setup() first.");
    return;
  }
  
  let label = GmailApp.getUserLabelByName(CONFIG.processedLabel);
  if (!label) {
    label = GmailApp.createLabel(CONFIG.processedLabel);
  }
  
  // Queries for HDFC UPI and Amazon Pay alerts (excluding already processed ones)
  const hdfcQuery = `from:alerts@hdfcbank.bank.in subject:"UPI txn" -label:${CONFIG.processedLabel}`;
  const amazonQuery = `from:no-reply@amazonpay.in subject:"successful" subject:"payment" -label:${CONFIG.processedLabel}`;
  
  processHdfcAlerts(hdfcQuery, sheet, label);
  processAmazonAlerts(amazonQuery, sheet, label);
}

// Parse and log HDFC UPI notifications
function processHdfcAlerts(query, sheet, label) {
  const threads = GmailApp.search(query, 0, 50);
  Logger.log(`Found ${threads.length} unprocessed HDFC UPI threads.`);
  
  threads.forEach(thread => {
    const messages = thread.getMessages();
    messages.forEach(message => {
      // Skip if the message has been labeled (sanity check)
      if (isThreadProcessed(thread, label)) return;
      
      const body = message.getPlainBody();
      
      // Extract properties via Regex
      const amountMatch = body.match(/Rs\.?\s*([\d,]+\.\d{2})/i);
      const accountMatch = body.match(/account ending (\d+)/i);
      const vpaMatch = body.match(/towards VPA\s+([a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+)/i);
      const merchantMatch = body.match(/towards VPA\s+[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\s*\(([^)]+)\)/i);
      const dateMatch = body.match(/on\s+(\d{2}-\d{2}-\d{2})/i);
      const refMatch = body.match(/(?:UPI transaction reference no\.|Ref no\.|Ref\.?)\s*:?\s*(\d+)/i);
      
      if (amountMatch) {
        const amount = parseFloat(amountMatch[1].replace(/,/g, ''));
        const account = accountMatch ? accountMatch[1] : "";
        const vpa = vpaMatch ? vpaMatch[1] : "";
        let merchant = merchantMatch ? merchantMatch[1].trim() : "";
        if (!merchant && vpa) merchant = vpa; // fallback to VPA
        const txnDate = dateMatch ? parseShortDate(dateMatch[1]) : message.getDate();
        const refId = refMatch ? refMatch[1] : "";
        
        sheet.appendRow([
          new Date(), // Current timestamp of run
          txnDate,    // Date transaction occurred
          "HDFC UPI",
          amount,
          merchant,
          account,
          refId,
          vpa,
          message.getId()
        ]);
      }
    });
    // Label thread as processed
    thread.addLabel(label);
  });
}

// Parse and log Amazon Pay notifications
function processAmazonAlerts(query, sheet, label) {
  const threads = GmailApp.search(query, 0, 50);
  Logger.log(`Found ${threads.length} unprocessed Amazon Pay threads.`);
  
  threads.forEach(thread => {
    const messages = thread.getMessages();
    messages.forEach(message => {
      if (isThreadProcessed(thread, label)) return;
      
      const body = message.getPlainBody();
      
      const payeeMatch = body.match(/Your payment to\s+(.*?)\s+is Approved/i);
      const amountMatch = body.match(/Amount:\s*₹?\s*([\d,]+\.?\d*)/i);
      
      if (amountMatch && payeeMatch) {
        const amount = parseFloat(amountMatch[1].replace(/,/g, ''));
        const merchant = payeeMatch[1].trim();
        const txnDate = message.getDate(); // Use email date since Amazon pay formats vary
        
        sheet.appendRow([
          new Date(),
          txnDate,
          "Amazon Pay",
          amount,
          merchant,
          "", // No account ending in email
          "", // No ref ID in email
          "", // No VPA in email
          message.getId()
        ]);
      }
    });
    thread.addLabel(label);
  });
}

// Helper: Check if thread already has processed label
function isThreadProcessed(thread, label) {
  const labels = thread.getLabels();
  for (let i = 0; i < labels.length; i++) {
    if (labels[i].getName() === label.getName()) {
      return true;
    }
  }
  return false;
}

// Helper: Parse HDFC short date format "dd-mm-yy" to Date object
function parseShortDate(dateStr) {
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1; // months are 0-indexed in JS
      // Assume 20xx for yy
      const year = 2000 + parseInt(parts[2], 10);
      return new Date(year, month, day);
    }
  } catch (e) {
    Logger.log("Date parsing failed for: " + dateStr);
  }
  return new Date();
}
