import ModSocket from './ModSocket'
import PedalboardManager from './PedalboardManager'
import EffectsManager from './EffectsManager'
import FileUploadManager from './FileUploadManager'

export default function Mod() {
  return (
    <ModSocket>
      <div class="space-y-4">
        <h1 class="text-2xl lcd-accent tracking-widest uppercase">Effects & Pedalboards</h1>
        <div class="lcd-divider"></div>
        <PedalboardManager>
          <EffectsManager />
        </PedalboardManager>
        <FileUploadManager />
      </div>
    </ModSocket>
  )
}
