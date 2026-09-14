On Error Resume Next
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
powerShell = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
scriptPath = root & "\ParticipantLauncher.ps1"
safeScriptPath = Replace(scriptPath, "'", "''")
' Remove the downloaded-file mark before starting PowerShell. This avoids a silent
' failure when the ZIP was downloaded from GitHub or another web site.
command = """" & powerShell & """" & " -NoProfile -STA -ExecutionPolicy Bypass -WindowStyle Hidden -Command " & """" & "$p='" & safeScriptPath & "'; Unblock-File -LiteralPath $p -ErrorAction SilentlyContinue; & $p" & """"
exitCode = shell.Run(command, 0, True)
If Err.Number <> 0 Then
  MsgBox "Could not start the Zotero bridge: " & Err.Description, 16, "Zotero Read-only Bridge"
ElseIf exitCode <> 0 Then
  MsgBox "The setup window could not be started. Try Start-Participant-Fallback.cmd in this folder.", 16, "Zotero Read-only Bridge"
End If
