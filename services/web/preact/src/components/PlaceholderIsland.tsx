import { createContext } from 'preact'
import { useState } from 'preact/hooks';

const CountContext = createContext()

export default function PlaceholderIsland() {
  const [placeholderCount, setPlaceholderCount] = useState(0)
  return (
    <CountContext.Provider value={placeholderCount}>
      <div class="text-center p-4 border-2 border-dashed border-lcd-500 rounded">
        <p class="text-lcd-300 font-bold mb-2">Interactive Component Placeholder</p>
        <p class="text-lcd-400 text-sm">Coming soon...</p>
        <CountContext.Consumer>
          {counter => (
            <p>{counter}</p>
          )}
        </CountContext.Consumer>
        <button onClick={() => setPlaceholderCount(placeholderCount + 1)}>Increase</button>
      </div>
    </CountContext.Provider>
  )
}
