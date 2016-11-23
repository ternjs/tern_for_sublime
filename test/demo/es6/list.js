export class List {
  constructor(head, tail) {
    this.head = head
    this.tail = tail
  }

  static of(...elements) {
    let result = null
    for (let i = elements.length - 1; i >= 0; i--)
      result = new List(elements[i], result)
    return result
  }

  map(f) {
    return new List(f(this.head), this.tail && this.tail.map(f))
  }

  *[Symbol.iterator]() {
    for (let pos = this; pos; pos = pos.tail)
      yield pos.head
  }
}
