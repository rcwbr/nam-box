import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions
} from '@headlessui/react'
import type { ComponentChildren } from 'preact'

interface SelectProps<T> {
  value: T | null
  options: T[]
  onChange: (value: T) => void
  placeholder?: string
  optionLabel: (option: T) => string
  optionKey?: (option: T) => string | number
  renderOption?: (option: T) => ComponentChildren
}

export default function Select<T>({
  value,
  options,
  onChange,
  placeholder = 'Select...',
  optionLabel,
  optionKey,
  renderOption
}: SelectProps<T>) {
  const loading = options.length < 1

  return (
    <Listbox
      value={value}
      onChange={(selected: T | null) => {
        if (selected !== null) {
          onChange(selected)
        }
      }}
    >
      <ListboxButton class="text-xs lcd-select">
        <span class="block truncate">
          {value ? optionLabel(value) : placeholder}
        </span>
        <svg class="h-4 w-4 text-lcd-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 011.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </ListboxButton>
      <ListboxOptions
        class="lcd-select-options"
        anchor="bottom start"
        transition
      >
        <div class="border-t-1 border-lcd-300"></div>
        {loading ? (
          <ListboxOption value={null} disabled class="lcd-select-option">
            Loading...
          </ListboxOption>
        ) : (
          options.map((option, index) => (
            <ListboxOption
              value={option}
              key={optionKey ? optionKey(option) : index}
              class="lcd-select-option"
            >
              {renderOption ? renderOption(option) : optionLabel(option)}
            </ListboxOption>
          ))
        )}
      </ListboxOptions>
    </Listbox>
  )
}