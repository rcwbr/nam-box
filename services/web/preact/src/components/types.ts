export interface ActiveEffect {
  uri: string
  params: { [symbol: string]: string | number }
}

export interface MidiCC {
  channel: number
  control: number
  hasRanges: boolean
  minimum: number
  maximum: number
}

export interface Port {
  valid: boolean
  symbol: string
  value: number
  midiCC: MidiCC
}

export interface Plugin {
  valid: boolean
  bypassed: boolean
  instanceNumber: number
  instance: string
  uri: string
  bypassCC: MidiCC
  x: number
  y: number
  ports: Port[]
  preset?: string
}

export interface PedalboardInfo {
  title: string
  width: number
  height: number
  factory: boolean
  midi_separated_mode: boolean
  midi_loopback: boolean
  plugins: Plugin[]
  connections: unknown[]
  hardware: {
    audio_ins: number
    audio_outs: number
    cv_ins: number
    cv_outs: number
    midi_ins: string[]
    midi_outs: string[]
    serial_midi_in: boolean
    serial_midi_out: boolean
    midi_merger_out: boolean
    midi_broadcaster_in: boolean
  }
  timeInfo: {
    available: number
    bpb: number
    bpbCC: MidiCC
    bpm: number
    bpmCC: MidiCC
    rolling: boolean
    rollingCC: MidiCC
  }
  version: number
}
