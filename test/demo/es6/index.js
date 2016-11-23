// Tern can do ECMAScript 6 (2015) too!

// Imports and exports work. You can complete module names, and
// jump to the definition of things defined in modules.

// (Press ctrl-. on `List` to jump to the class definition)
import {List} from "./list"

import * as myMath from "./mymath"

const l = List.of(3, 4, 5)
for (let elt of l.map(x => x * 2)) {
  // Tern knows that `elt` is a number!
  let output = myMath.halve(elt)
  console.log(output)
}

// Raw template string
let raw = String.raw`\n`

// Default arguments
Array.of(1, 2, 3, 4).find(x => x % 3 == 0)
