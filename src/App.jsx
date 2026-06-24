import "./styles.css"
import { useState } from "react";

const { webUtils } = eval("require('electron')");
const fs = eval("require('fs')");

function App() {
    const [file, setFile] = useState(null);
    const [mtlPath, setMtlPath] = useState(null);
    const [status, setStatus] = useState("Please select a file and submit");
    const [progress, setProgress] = useState(0);
    const [files, setFiles] = useState([]);

    const submissionHandler = async () => {
        for (const file of files) {
            const realPath = webUtils.getPathForFile(file);
            const mtlFilePath = realPath.replace(".obj", ".mtl");
            const mtlData = fs.readFileSync(mtlFilePath);
            const mtlBlob = new Blob([mtlData]);

            const formData = new FormData();
            formData.append("file", file);
            formData.append("mtl", mtlBlob, file.name.replace(".obj", ".mtl"));
            formData.append("originalPath", realPath);

            // send upload but don't await it
            fetch("http://127.0.0.1:5000/upload", {
                method: "POST",
                body: formData
            });

            // wait for progress to hit 100
            await new Promise((resolve) => {
                setProgress(0);
                const poll = setInterval(async () => {
                    try {
                        const res = await fetch("http://127.0.0.1:5000/progress");
                        const data = await res.json();
                        setProgress(data.value);
                        setStatus(data.message);
                        if (data.value >= 100) {
                            clearInterval(poll);
                            resolve();
                        }
                    } catch (e) { }
                }, 20);
            });
        }

    }

    return (
        <div>
            <h1 className="title" >Roblox to Mesh</h1>

            <div className="fileForm" method="post">
                <h3 className = "fileLabel" htmlFor="inputFile">Select an OBJ File</h3>

                <div className="fileDiv">
                    <input
                        id="inputFile"
                        type="file"
                        accept=".obj"
                        multiple
                        onChange={(e) => {
                            const objs = Array.from(e.target.files);
                            setFiles(objs);
                            const realPath = webUtils.getPathForFile(objs[0]);
                            setMtlPath(realPath.replace(".obj", ".mtl"));
                        }}
                    />
                    <br />

                    <button onClick={submissionHandler}>Submit</button>
                </div>
            </div>

            <pre className="operationStatus">
                <p className="operationText" id="loadingText">...</p>
                <p className="operationText">{status}</p>
            </pre>
            <div className="loadingBarParent">
                <div className="loadingBar" style={{ width: `${progress}%` }}></div>
            </div>

            <div className="info">
                {/*}<p><b>Developed by EpoxTime</b></p>*/}
            </div>
        </div>
    )
}

export default App;