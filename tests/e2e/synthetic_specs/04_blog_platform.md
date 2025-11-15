# Blog Platform - Level 2 Synthetic Spec

## Overview
Full-featured blog platform with Next.js 14, PostgreSQL, Markdown support, and role-based authentication. Public blog with admin dashboard for content management.

## Tech Stack
- **Frontend**: Next.js 14 (App Router), React 18, Tailwind CSS, shadcn/ui
- **Backend**: Next.js API Routes (serverless functions)
- **Database**: PostgreSQL 15 (via Prisma ORM)
- **Auth**: NextAuth.js v5 (OAuth + Credentials)
- **Markdown**: react-markdown, remark-gfm, gray-matter
- **Images**: Cloudinary or next/image with local storage
- **Deployment**: Vercel or Docker
- **Testing**: Vitest, Testing Library, Playwright

## Features

### F1: Public Blog
- Homepage with latest posts (paginated, 10 per page)
- Individual post pages with full content
- Post metadata: title, author, date, reading time, tags
- Markdown rendering with syntax highlighting
- Table of contents (auto-generated from headings)
- Related posts sidebar (by tags)
- SEO optimization (meta tags, Open Graph, structured data)
- RSS feed generation

### F2: Authentication & Authorization
- User roles: admin, author, reader
- OAuth login (Google, GitHub)
- Email/password login (for authors/admins)
- Role-based access control:
  - Admin: Full access (create, edit, delete all posts, manage users)
  - Author: Create and edit own posts, submit for review
  - Reader: View published posts only
- Session management (NextAuth.js)
- Protected routes for dashboard

### F3: Admin Dashboard
- Posts management table (title, author, status, published date)
- Create new post (Markdown editor with preview)
- Edit existing post
- Delete post (with confirmation)
- Publish/unpublish toggle
- Draft saving (auto-save every 30 seconds)
- Post scheduling (publish at future date)
- User management (admin only)
- Analytics dashboard (views, popular posts)

### F4: Markdown Editor
- Split-pane editor: Markdown input + live preview
- Toolbar: Bold, italic, headings, lists, links, images, code blocks
- Image upload with drag-and-drop
- Keyboard shortcuts (Ctrl+B for bold, etc.)
- Front matter support (title, date, tags, excerpt, cover_image)
- Syntax highlighting for code blocks (Prism.js)
- Auto-save drafts to localStorage (fallback)

### F5: Post Management
- Post statuses: draft, review, published, archived
- Status workflow:
  - Author creates draft → submits for review
  - Admin reviews → publishes or requests changes
  - Published posts visible on public blog
- Version history (save snapshots on publish)
- Post scheduling (publish_at timestamp)
- Slug generation from title (auto + manual override)
- Tags management (create, assign, filter by tag)

### F6: Search & Discovery
- Full-text search (post title, content, tags)
- Filter by: author, tag, date range, status
- Sort by: date (newest/oldest), views, title (A-Z)
- Tag cloud on homepage
- Archive page (posts grouped by month/year)
- Search results page with highlighting

### F7: Comments System (Optional Bonus)
- Readers can comment on published posts
- Comment moderation (admin approval required)
- Nested replies (1 level deep)
- Comment like/dislike
- Markdown support in comments
- Spam detection (simple keyword filter)

### F8: Analytics
- Post view tracking (increment on page load)
- Popular posts widget (top 5 by views)
- Author statistics (total posts, total views)
- Dashboard charts (views over time)
- Daily/weekly/monthly view breakdown

## Architecture

### Frontend Structure
```
src/
├── app/
│   ├── (public)/
│   │   ├── page.tsx (homepage)
│   │   ├── posts/[slug]/page.tsx
│   │   ├── tags/[tag]/page.tsx
│   │   ├── archive/page.tsx
│   │   └── search/page.tsx
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx
│   │   ├── page.tsx (overview)
│   │   ├── posts/page.tsx (posts table)
│   │   ├── posts/new/page.tsx (create)
│   │   ├── posts/[id]/edit/page.tsx
│   │   ├── users/page.tsx (admin only)
│   │   └── analytics/page.tsx
│   ├── api/
│   │   ├── auth/[...nextauth]/route.ts
│   │   ├── posts/route.ts
│   │   ├── posts/[id]/route.ts
│   │   ├── upload/route.ts
│   │   └── analytics/route.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── blog/
│   │   ├── PostCard.tsx
│   │   ├── PostContent.tsx (Markdown renderer)
│   │   ├── PostMeta.tsx
│   │   ├── RelatedPosts.tsx
│   │   ├── TagCloud.tsx
│   │   └── CommentSection.tsx
│   ├── editor/
│   │   ├── MarkdownEditor.tsx
│   │   ├── EditorToolbar.tsx
│   │   └── ImageUpload.tsx
│   ├── dashboard/
│   │   ├── PostsTable.tsx
│   │   ├── StatsCard.tsx
│   │   └── AnalyticsChart.tsx
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Sidebar.tsx
│   └── ui/ (shadcn/ui)
├── lib/
│   ├── prisma.ts
│   ├── auth.ts (NextAuth config)
│   ├── markdown.ts (parsing utilities)
│   └── utils.ts
└── prisma/
    ├── schema.prisma
    └── migrations/
```

## Database Schema (Prisma)

### User Model
```prisma
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  username      String    @unique
  name          String?
  password      String?   // Hashed, nullable for OAuth users
  role          Role      @default(READER)
  avatar        String?
  bio           String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  posts         Post[]
  comments      Comment[]

  @@index([email])
  @@index([username])
}

enum Role {
  ADMIN
  AUTHOR
  READER
}
```

### Post Model
```prisma
model Post {
  id            String    @id @default(uuid())
  slug          String    @unique
  title         String
  excerpt       String?   // Short description
  content       String    @db.Text // Markdown content
  coverImage    String?
  status        PostStatus @default(DRAFT)
  publishedAt   DateTime?
  scheduledAt   DateTime? // For scheduled publishing
  authorId      String
  author        User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  views         Int       @default(0)
  readingTime   Int       @default(0) // Minutes
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  tags          Tag[]     @relation("PostTags")
  comments      Comment[]
  versions      PostVersion[]

  @@index([slug])
  @@index([authorId])
  @@index([status])
  @@index([publishedAt])
  @@index([createdAt])
}

enum PostStatus {
  DRAFT
  REVIEW
  PUBLISHED
  ARCHIVED
}
```

### Tag Model
```prisma
model Tag {
  id        String   @id @default(uuid())
  name      String   @unique
  slug      String   @unique
  posts     Post[]   @relation("PostTags")
  createdAt DateTime @default(now())

  @@index([slug])
}
```

### Comment Model
```prisma
model Comment {
  id          String    @id @default(uuid())
  content     String    @db.Text
  postId      String
  post        Post      @relation(fields: [postId], references: [id], onDelete: Cascade)
  authorId    String
  author      User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  parentId    String?   // For nested replies
  parent      Comment?  @relation("CommentReplies", fields: [parentId], references: [id])
  replies     Comment[] @relation("CommentReplies")
  approved    Boolean   @default(false)
  likes       Int       @default(0)
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt

  @@index([postId])
  @@index([authorId])
  @@index([approved])
}
```

### PostVersion Model (Audit Trail)
```prisma
model PostVersion {
  id          String   @id @default(uuid())
  postId      String
  post        Post     @relation(fields: [postId], references: [id], onDelete: Cascade)
  title       String
  content     String   @db.Text
  versionNum  Int
  createdAt   DateTime @default(now())

  @@index([postId])
  @@index([createdAt])
}
```

## API Endpoints (Next.js API Routes)

### Posts
**GET /api/posts**
- Query: `?page=1&limit=10&status=published&tag=nextjs&author=user-id&search=keyword&sort=date&order=desc`
- Response: `{posts: [...], total, page, totalPages}`
- Auth: Optional (filters by published for unauthenticated)

**GET /api/posts/[id]**
- Response: Full post object
- Side effect: Increment view count
- Auth: Optional (only published posts for unauthenticated)

**POST /api/posts**
- Auth: Required (Author/Admin)
- Request: `{title, content, excerpt?, coverImage?, tags: [], status}`
- Response: Created post object

**PUT /api/posts/[id]**
- Auth: Required (Author: own posts, Admin: all posts)
- Request: `{title?, content?, excerpt?, coverImage?, tags?, status?}`
- Response: Updated post object

**DELETE /api/posts/[id]**
- Auth: Required (Admin only)
- Response: `{success: true}`

**POST /api/posts/[id]/publish**
- Auth: Required (Admin only)
- Response: Published post object

### Authentication
**POST /api/auth/register**
- Request: `{email, username, password, name?}`
- Response: User object (without password)

**POST /api/auth/[...nextauth]**
- NextAuth.js routes (signin, signout, callback, etc.)

### Upload
**POST /api/upload**
- Auth: Required (Author/Admin)
- Request: FormData with image file
- Response: `{url: "uploaded-image-url"}`
- Validation: Max 5MB, jpeg/png/webp only

### Analytics
**GET /api/analytics/stats**
- Auth: Required (Author: own stats, Admin: all stats)
- Response: `{totalPosts, totalViews, popularPosts: [...], viewsByDay: [...]}`

**GET /api/analytics/views/[postId]**
- Auth: Required (Author/Admin)
- Response: `{views: 123, viewsByDay: [...]}`

### Comments
**GET /api/posts/[postId]/comments**
- Query: `?approved=true`
- Response: Comment tree (nested replies)
- Auth: Optional (only approved comments for unauthenticated)

**POST /api/posts/[postId]/comments**
- Auth: Required (Reader/Author/Admin)
- Request: `{content, parentId?}`
- Response: Created comment (approved=false by default)

**PUT /api/comments/[id]/approve**
- Auth: Required (Admin only)
- Response: Approved comment

**DELETE /api/comments/[id]**
- Auth: Required (Comment author or Admin)
- Response: `{success: true}`

## Markdown Features

### Supported Syntax
- Headings (H1-H6)
- Bold, italic, strikethrough
- Ordered and unordered lists
- Links and images
- Code blocks with syntax highlighting
- Blockquotes
- Tables
- Horizontal rules
- Task lists (GitHub Flavored Markdown)

### Front Matter
```markdown
---
title: "My Blog Post"
date: "2024-01-15"
excerpt: "Short description for SEO"
coverImage: "/images/cover.jpg"
tags: ["nextjs", "react", "typescript"]
---

# Post Content Starts Here
```

### Code Highlighting
- Languages: JavaScript, TypeScript, Python, Rust, Go, HTML, CSS
- Line numbers optional
- Copy button for code blocks
- Theme: VS Code Dark+ or GitHub Light

## SEO & Performance

### Meta Tags (per post)
```tsx
<title>{post.title} | Blog Name</title>
<meta name="description" content={post.excerpt} />
<meta property="og:title" content={post.title} />
<meta property="og:description" content={post.excerpt} />
<meta property="og:image" content={post.coverImage} />
<meta property="og:type" content="article" />
<meta name="twitter:card" content="summary_large_image" />
```

### Structured Data
```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Post Title",
  "image": "cover-image-url",
  "author": {
    "@type": "Person",
    "name": "Author Name"
  },
  "datePublished": "2024-01-15",
  "dateModified": "2024-01-20"
}
```

### Performance Optimizations
- Static generation for published posts (ISR with 60s revalidation)
- Dynamic rendering for drafts/admin pages
- Image optimization with next/image
- Code splitting for editor (dynamic import)
- Database query optimization (select only needed fields)
- Pagination to limit data transfer

## Validation Rules

### Post Creation/Edit
- Title: 1-200 chars, required
- Content: Min 100 chars, required
- Excerpt: Max 300 chars, optional
- Slug: Auto-generated, alphanumeric + hyphens, unique
- Tags: Max 5 tags per post
- Cover image: Max 5MB, jpeg/png/webp

### User Registration
- Email: Valid email format, unique
- Username: 3-30 chars, alphanumeric + underscore, unique
- Password: Min 8 chars, 1 uppercase, 1 number
- Name: Max 100 chars

### Comments
- Content: 1-1000 chars, required
- Must be authenticated
- Profanity filter (basic keyword check)

## Error Handling

### Frontend
- Form validation errors inline
- Toast notifications for API errors
- Error boundaries for React errors
- 404 page for invalid post slugs
- Loading skeletons during data fetch

### Backend
- 400: Validation errors
- 401: Unauthorized (not logged in)
- 403: Forbidden (insufficient role)
- 404: Post/User/Comment not found
- 409: Conflict (duplicate slug/email/username)
- 500: Internal server error (log to console)

## Performance Requirements

### Frontend
- Homepage load: < 2s (LCP)
- Post page load: < 1.5s (static), < 3s (dynamic)
- Editor responsiveness: < 100ms input lag
- Search results: < 500ms
- Lighthouse Performance: ≥ 85

### Backend/Database
- List posts query: < 150ms
- Single post query: < 100ms
- Create/update post: < 300ms
- Search query (full-text): < 200ms
- Analytics queries: < 500ms

### Database Optimization
- Indexes on frequently queried columns
- Pagination to limit result sets
- Select only required fields (Prisma select)
- Avoid N+1 queries (Prisma include with care)

## Docker Compose (Optional)

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/blog
      NEXTAUTH_SECRET: your-secret-key
      NEXTAUTH_URL: http://localhost:3000
      GOOGLE_CLIENT_ID: your-google-client-id
      GOOGLE_CLIENT_SECRET: your-google-client-secret
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: blog
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

## Test Coverage Requirements

### Frontend Tests
- Unit tests: ≥ 90% coverage
- Components: PostCard, MarkdownEditor, PostsTable
- Utilities: Markdown parsing, slug generation
- Hooks: useAuth, usePosts

### Backend Tests
- API routes: All endpoints
- Auth middleware: Role validation
- Database queries: CRUD operations
- Coverage: ≥ 90%

### E2E Tests (30 scenarios)
1. View homepage with latest posts
2. Navigate to individual post page
3. Verify Markdown rendering (headings, code, lists)
4. Search posts by keyword
5. Filter posts by tag
6. View posts by author
7. Navigate archive page (grouped by month)
8. Register new user (author role)
9. Login with email/password
10. Login with Google OAuth
11. Logout
12. Access dashboard (authenticated)
13. Access dashboard (unauthenticated - redirect to login)
14. Create new draft post
15. Save draft (auto-save)
16. Upload cover image
17. Add tags to post
18. Preview post in editor
19. Submit post for review (author)
20. Publish post (admin)
21. Schedule post for future date
22. Edit existing post (author: own post)
23. Edit existing post (author: other's post - forbidden)
24. Delete post (admin only)
25. View post analytics (views, chart)
26. Add comment to post (authenticated)
27. Approve comment (admin)
28. Delete comment (admin)
29. View user management page (admin only)
30. RSS feed generation and validation

## Success Criteria

1. ✅ Public blog displays published posts
2. ✅ Authentication working (OAuth + Credentials)
3. ✅ Role-based access control enforced
4. ✅ Markdown editor functional with preview
5. ✅ Image upload working
6. ✅ Post CRUD operations complete
7. ✅ Post status workflow (draft → review → published)
8. ✅ Tags system functional
9. ✅ Search and filtering working
10. ✅ Comments system with moderation (if implemented)
11. ✅ Analytics dashboard with view tracking
12. ✅ SEO optimized (meta tags, structured data, RSS)
13. ✅ All E2E tests passing (30 scenarios)
14. ✅ Test coverage ≥90%
15. ✅ Performance requirements met
16. ✅ Responsive design (mobile, tablet, desktop)
17. ✅ Database migrations applied successfully
18. ✅ Error handling comprehensive
19. ✅ Reading time calculation accurate
20. ✅ Slug generation and uniqueness enforced
