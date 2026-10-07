---
status: complete
---

# DLC-Matcher wartet auf den UI-Refresh

Nach einer PC-DLC-Metadatenauswahl muss die ROM-Ansicht den aktualisierten Datensatz laden, bevor der Dialog schließt. Der Refresh wird als awaitbarer Callback vom PC-Komponentenbereich an den Matcher übergeben.
