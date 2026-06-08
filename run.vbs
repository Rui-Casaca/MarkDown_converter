Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batchFile = scriptDir & "\.pdf_to_md_internal\1 - run_aux.bat"

shell.CurrentDirectory = scriptDir
shell.Run Chr(34) & batchFile & Chr(34), 0, False
