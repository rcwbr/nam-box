/**
 * Types generated from mod-api OpenAPI schema.
 * These replace the old types.ts with proper API-aligned types.
 */

// Base types matching OpenAPI schemas
export interface Pedalboard {
  id: number
  name: string
  file: string
  effects: Record<number, EffectInstance>
  connections: Record<number, Connection>
}

export interface EffectInstance {
  id: number
  uri: string
  name: string | null
  ports: Port[]
  parameters: Record<string, Parameter>
}

export interface EffectInfo {
  uri: string
  name: string | null
  ports: Port[]
  parameters: Record<string, ParameterType>
}

export interface Port {
  name: string
  type: string
  owner_type: string | null
  effect_instance_id: number | null
}

// Parameter types - base definitions (without value)
export interface NumberParameterType {
  name: string
  type: 'number'
  min: number
  max: number
  default: number
}

export interface FilenameParameterType {
  name: string
  type: 'filename'
  default: string
}

export type ParameterType = NumberParameterType | FilenameParameterType

// Concrete parameters - extend Type with value field
export interface NumberParameter extends NumberParameterType {
  value: number
}

export interface FilenameParameter extends FilenameParameterType {
  value: string
}

export type Parameter = NumberParameter | FilenameParameter

// Connection type (matches OpenAPI Connection schema)
export interface Connection {
  id: number
  input_port_id: string
  output_port_id: string
}

// API Request/Response types
export interface CreatePedalboardRequest {
  name: string
  duplicate_current?: boolean
}

export interface CreateConnectionRequest {
  input_port_id: string
  output_port_id: string
}

export interface CreateEffectRequest {
  effect_uri: string
  name?: string | null
}

export interface RenamePedalboardRequest {
  name: string
}

export interface SetParameterRequest {
  value: number | string
}

// File info for NAM model selection (from /api/model/all)
export interface FileInfo {
  name: string
  size: number
  path: string
}