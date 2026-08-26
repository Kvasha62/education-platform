import type { ArticleBlock, ContentBody } from '../content'

const ArticleBlockView = ({ block }: { block: ArticleBlock }) => {
  if (block.type === 'paragraph') return <p>{block.text}</p>
  if (block.type === 'heading') {
    return <div className="student-body-heading" role="heading" aria-level={block.level}>{block.text}</div>
  }
  if (block.type === 'code') {
    return <pre><code data-language={block.language ?? undefined}>{block.code}</code></pre>
  }
  if (block.type === 'list') {
    const List = block.style === 'ordered' ? 'ol' : 'ul'
    return <List>{block.items.map((item, index) => <li key={index}>{item}</li>)}</List>
  }
  return (
    <p>
      <a href={block.url} rel="noreferrer" target="_blank">{block.label}</a>
    </p>
  )
}

export const StudentContentBody = ({ body }: { body: ContentBody }) => {
  if (body.kind === 'resource') {
    return (
      <div className="student-resource">
        {body.resource.url ? (
          <a href={body.resource.url} rel="noreferrer" target="_blank">Open resource</a>
        ) : (
          <p>Resource unavailable.</p>
        )}
        {body.resource.description && <p>{body.resource.description}</p>}
      </div>
    )
  }
  return (
    <div className="student-article">
      {body.blocks.map((block, index) => <ArticleBlockView block={block} key={index} />)}
    </div>
  )
}
