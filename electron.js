const { app, BrowserWindow, Menu } = require('electron')
const path = require('path')

const menu = Menu.buildFromTemplate([
    {
        label: 'Application',
        submenu: [
            { role: 'quit' },
            { label: 'Restart' },
            { label: 'Report Bug' }
        ]
    },
    {
        label: 'View',
        submenu: [
            {role: 'reload'}
        ]
    }
])

Menu.setApplicationMenu(menu)

//---------------

const windowSize = 50
const windowRatio = [16, 12]

function createWindow() {
    const win = new BrowserWindow({
        width: windowRatio[0] * windowSize,
        height: windowRatio[1] * windowSize,
        resizable: false,

        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    })

    win.setIcon(path.join(__dirname, 'src/assets/images/applicationIcon.ico'))

    win.setAspectRatio(windowRatio[0] * windowSize / windowRatio[1] * windowSize)

    win.loadURL('http://localhost:1234')

    win.webContents.openDevTools()
}

app.whenReady().then(createWindow)