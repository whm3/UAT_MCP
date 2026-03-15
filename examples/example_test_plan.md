# Example UAT Test Plan

## Pre-Test: Environment Setup

| # | Test | Expected | Pass |
|---|------|----------|------|
| 0.1 | Open the application URL in a browser | Page loads without errors | |
| 0.2 | Check that the page title is correct | Title matches expected value | |

## 1. User Authentication

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Navigate to the login page | Login form is displayed with username and password fields | |
| 1.2 | Enter valid credentials and click Login | User is redirected to the dashboard | |
| 1.3 | Enter an invalid password and click Login | Error message is displayed, user stays on login page | |
| 1.4 | Click the Logout button | User is redirected to the login page, session is ended | |

## 2. Dashboard

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Log in and view the dashboard | Dashboard displays user name and summary statistics | |
| 2.2 | Click the Settings link | Settings page opens with current user preferences | |
| 2.3 | Resize the browser window to mobile width | Layout adapts to single-column responsive design | |

## 3. Data Entry

| # | Test | Expected | Pass |
|---|------|----------|------|
| 3.1 | Click the New Entry button | Empty form is displayed with all required fields | |
| 3.2 | Fill in all fields and click Save | Entry is saved, success message shown, entry appears in list | |
| 3.3 | Leave a required field empty and click Save | Validation error is shown for the missing field | |
| 3.4 | Edit an existing entry and click Save | Changes are saved, updated values shown in list | |
| 3.5 | Delete an entry and confirm the prompt | Entry is removed from the list | |
