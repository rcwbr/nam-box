import { createContext } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import {
  Button,
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
  Input,
} from '@headlessui/react'

interface FileInfo {
  name: string
  size: number
  path: string
}

const FilesContext = createContext<Array<FileInfo>>([])

export default function FileUploadManager() {
  const [filesState, setFilesState] = useState<Array<FileInfo>>([])
  const [uploadFileOpen, setUploadFileOpen] = useState<boolean>(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const loadFiles = async () => {
    const response = await fetch('/api/model/all')
    if (!response.ok) throw new Error('Failed to load files')
    const results = await response.json()
    setFilesState(results as FileInfo[])
  }

  const uploadFile = async () => {
    if (selectedFiles.length === 0) return

    // Upload all files in a single request using the multiple endpoint
    const formData = new FormData()
    for (const file of selectedFiles) {
      formData.append('files', file)
    }

    const response = await fetch('/api/model/upload/multiple', {
      method: 'POST',
      body: formData
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to upload files: ${error}`)
    }

    setUploadFileOpen(false)
    setSelectedFiles([])
    loadFiles()
  }

  const deleteFile = async (filename: string) => {
    const response = await fetch(`/api/model/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error(`Failed to delete file ${filename}`)
    loadFiles()
  }

  useEffect(() => {
    loadFiles()
  }, [])

  return (
    <FilesContext.Provider value={filesState}>
      <div class="space-y-3">
        <h2 class="text-xs lcd-text text-center uppercase tracking-widest">Model Files</h2>
        <div class="space-y-1 pr-1">
          {filesState.length < 1 ? (
            <p class="text-lcd-400 text-xs">No model files found</p>
          ) : (
            filesState.map((file: FileInfo) => (
              <div key={file.name} class="flex items-center justify-between p-2 bg-black border-1 rounded-sm">
                <div>
                  <p class="text-lcd-200 font-bold text-xs">{file.name}</p>
                </div>
                <div class="flex items-center gap-2">
                  <a
                    href={`/api/model/${encodeURIComponent(file.name)}`}
                    download
                    class="text-lcd-300 hover:text-lcd-200 text-xs"
                  >
                    Download
                  </a>
                  <button
                    class="text-lcd-300 hover:text-lcd-200 text-xs"
                    onClick={() => deleteFile(file.name)}
                  >
                    X
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div class="border-t-1 border-lcd-300"></div>

        <Button
          class="lcd-button w-full"
          onClick={() => setUploadFileOpen(true)}
        >
          UPLOAD FILES
        </Button>
      </div>

      <Dialog open={uploadFileOpen} onClose={setUploadFileOpen} class="relative z-10">
        <DialogBackdrop
          transition
          class="fixed inset-0 bg-black/80 flex items-center justify-center transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
        />
        <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <DialogPanel
              transition
              class="relative transform overflow-hidden text-center shadow-xl transition-all data-closed:translate-y-4 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-lg data-closed:sm:translate-y-0 data-closed:sm:scale-95"
            >
              <div class="lcd-panel p-4">
                <DialogTitle class="text-xs lcd-text uppercase tracking-widest mb-2">Upload Model Files</DialogTitle>

                <div class="mb-3">
                  <Input
                    type="file"
                    accept=".nam"
                    multiple
                    class="lcd-input text-xs w-full p-2 bg-lcd-700 rounded-sm"
                    onChange={(e: Event) => {
                      const target = e.target as HTMLInputElement
                      const files = Array.from(target.files || [])
                      if (files.length > 0) setSelectedFiles(files)
                    }}
                  />
                  {selectedFiles.length > 0 && (
                    <p class="text-lcd-400 text-xs mt-1">
                      {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected
                    </p>
                  )}
                </div>

                <div class="flex gap-2">
                  <Button
                    class="lcd-button"
                    onClick={() => {
                      setUploadFileOpen(false)
                      setSelectedFiles([])
                    }}
                  >
                    CANCEL
                  </Button>
                  <Button
                    class="lcd-button"
                    onClick={uploadFile}
                    disabled={selectedFiles.length === 0}
                  >
                    UPLOAD
                  </Button>
                </div>
              </div>
            </DialogPanel>
          </div>
        </div>
      </Dialog>
    </FilesContext.Provider>
  )
}

export { FilesContext }
