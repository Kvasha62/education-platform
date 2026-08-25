export interface ParagraphBlock {
  type: 'paragraph'
  text: string
}

export interface HeadingBlock {
  type: 'heading'
  level: number
  text: string
}

export interface CodeBlock {
  type: 'code'
  language?: string | null
  code: string
}

export interface ListBlock {
  type: 'list'
  style: 'ordered' | 'unordered'
  items: string[]
}

export interface LinkBlock {
  type: 'link'
  url: string
  label: string
}

export type ArticleBlock =
  | ParagraphBlock
  | HeadingBlock
  | CodeBlock
  | ListBlock
  | LinkBlock

export interface ArticleBody {
  schema_version: 1
  kind: 'article'
  blocks: ArticleBlock[]
}

export interface ResourceBody {
  schema_version: 1
  kind: 'resource'
  resource: {
    url: string | null
    description: string
  }
}

export type ContentBody = ArticleBody | ResourceBody
export type ArticleBlockType = ArticleBlock['type']

export const createBlock = (type: ArticleBlockType): ArticleBlock => {
  if (type === 'paragraph') return { type, text: '' }
  if (type === 'heading') return { type, level: 2, text: '' }
  if (type === 'code') return { type, language: null, code: '' }
  if (type === 'list') return { type, style: 'unordered', items: [] }
  return { type, url: 'https://', label: '' }
}
