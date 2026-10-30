param([string]$AppUrl='')
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$form=New-Object System.Windows.Forms.Form
$form.Text='MTR Soft · Flux Storage browser setup'
$form.Size=New-Object System.Drawing.Size(560,400)
$form.StartPosition='CenterScreen'
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
$form.Font=New-Object System.Drawing.Font('Segoe UI',10)
$form.BackColor=[System.Drawing.Color]::White
$title=New-Object System.Windows.Forms.Label
$title.Text='Choose a browser. Stay in control.'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.SetBounds(25,25,500,35)
$form.Controls.Add($title)
$description=New-Object System.Windows.Forms.Label
$description.Text="Flux uses a local browser interface. Nothing is installed automatically. Select a browser below; Windows Package Manager will download it only after your confirmation."
$description.SetBounds(25,75,490,65)
$form.Controls.Add($description)
$choices=New-Object System.Windows.Forms.ComboBox
$choices.DropDownStyle='DropDownList'
$choices.Items.AddRange(@('Microsoft Edge','Google Chrome','Mozilla Firefox','Brave'))
$choices.SelectedIndex=0
$choices.SetBounds(25,155,490,32)
$form.Controls.Add($choices)
$consent=New-Object System.Windows.Forms.CheckBox
$consent.Text='I want to download/install this browser and accept its installer agreements.'
$consent.SetBounds(25,200,490,48)
$form.Controls.Add($consent)
$install=New-Object System.Windows.Forms.Button
$install.Text='Download && install selected browser'
$install.Enabled=$false
$install.FlatStyle='Flat'
$install.SetBounds(25,265,325,42)
$form.Controls.Add($install)
$cancel=New-Object System.Windows.Forms.Button
$cancel.Text='Not now'
$cancel.SetBounds(370,265,145,42)
$cancel.Add_Click({$form.DialogResult=[System.Windows.Forms.DialogResult]::Cancel;$form.Close()})
$form.Controls.Add($cancel)
$script:installProcess=$null
$timer=New-Object System.Windows.Forms.Timer
$timer.Interval=500
$timer.Add_Tick({
    if ($script:installProcess -and $script:installProcess.HasExited) {
        $timer.Stop()
        $code=$script:installProcess.ExitCode
        $script:installProcess.Dispose()
        $script:installProcess=$null
        $choices.Enabled=$true
        $consent.Enabled=$true
        $cancel.Enabled=$true
        if ($code -eq 0) {
            if ($AppUrl -match '^http://127\.0\.0\.1:\d+/?$') {Start-Process $AppUrl}
            $form.DialogResult=[System.Windows.Forms.DialogResult]::OK
            $form.Close()
        } else {
            $description.Text="Installer returned exit code $code. No success is assumed. Retry or use the browser publisher's official installer."
            $install.Enabled=$consent.Checked
        }
    }
})
$form.Add_FormClosing({param($sender,$eventArgs) if ($script:installProcess) {$eventArgs.Cancel=$true}})
$consent.Add_CheckedChanged({$install.Enabled=$consent.Checked})
$install.Add_Click({
    $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        [System.Windows.Forms.MessageBox]::Show('Windows Package Manager (App Installer) is not available. Install a browser using an official installer or install Microsoft App Installer, then reopen Flux. No software was installed.','MTR Soft · Setup unavailable','OK','Information')|Out-Null
        return
    }
    $ids=@('Microsoft.Edge','Google.Chrome','Mozilla.Firefox','Brave.Brave')
    $id=$ids[$choices.SelectedIndex]
    $answer=[System.Windows.Forms.MessageBox]::Show("Download and install $($choices.SelectedItem) using the winget community source? Administrator approval and internet access may be required.",'MTR Soft · Confirm browser installation','YesNo','Question')
    if ($answer -ne 'Yes') {return}
    $install.Enabled=$false
    $description.Text='Windows Package Manager is opening. Finish its installer, then return to Flux. Installation is visible, not silent.'
    try {
        $script:installProcess=Start-Process -FilePath $winget.Source -ArgumentList @('install','--id',$id,'--exact','--source','winget','--accept-source-agreements','--accept-package-agreements') -PassThru
        $choices.Enabled=$false
        $consent.Enabled=$false
        $cancel.Enabled=$false
        $timer.Start()
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Installation did not finish: $($_.Exception.Message)`nNo success is assumed. You may retry or install from the browser publisher's official installer.",'MTR Soft · Browser setup','OK','Warning')|Out-Null
        $install.Enabled=$consent.Checked
    }
})
$result=$form.ShowDialog()
$timer.Dispose()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {exit 0}
exit 1
