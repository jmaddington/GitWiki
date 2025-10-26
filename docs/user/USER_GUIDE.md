# GitWiki User Guide

Welcome to GitWiki! This guide will help you get started with creating, editing, and managing wiki content.

## Table of Contents

- [Getting Started](#getting-started)
- [Browsing Wiki Pages](#browsing-wiki-pages)
- [Creating and Editing Pages](#creating-and-editing-pages)
- [Working with Images](#working-with-images)
- [Understanding Conflict Resolution](#understanding-conflict-resolution)
- [Markdown Syntax Guide](#markdown-syntax-guide)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

### What is GitWiki?

GitWiki is a Git-backed wiki system that combines the simplicity of a wiki with the power of version control. Every change is tracked, and you can collaborate with multiple editors simultaneously.

### Accessing GitWiki

1. Open your web browser and navigate to your GitWiki installation URL
2. You'll see the wiki home page with a list of available pages
3. Click on any page to view its content

### Navigation

- **Home**: Click the "Home" link or logo to return to the wiki home page
- **Search**: Use the search box in the navigation bar to find pages
- **Breadcrumbs**: Navigate through page hierarchies using breadcrumb links
- **Edit Button**: Click "Edit" on any page to start editing (if you have permission)

---

## Browsing Wiki Pages

### Viewing Pages

Wiki pages are displayed with:
- **Content**: The main page content rendered from Markdown
- **Table of Contents**: Automatically generated from page headings
- **Metadata**: Last edited date, author, and commit history
- **Edit Button**: Quick access to editing mode

### Searching for Content

1. Click the search box in the navigation bar
2. Enter your search terms
3. Press Enter or click the search icon
4. Results are ranked by relevance:
   - Pages with matching titles rank higher
   - Number of matches is displayed
   - Search snippets show context

**Search Tips:**
- Search is case-insensitive
- Use specific terms for better results
- Phrases are matched exactly as typed

### Viewing Page History

To see the history of changes to a page:

1. Navigate to the page you want to review
2. Click the "History" button
3. You'll see a list of all commits affecting this page:
   - Commit date and time
   - Author name and email
   - Commit message
   - Number of additions/deletions

---

## Creating and Editing Pages

### Starting an Edit Session

1. Navigate to the page you want to edit (or create a new page URL)
2. Click the "Edit" button
3. GitWiki will:
   - Create a draft branch for your changes
   - Load the current content into the editor
   - Start auto-saving your work

### Using the Markdown Editor

GitWiki uses a powerful Markdown editor with these features:

**Toolbar Buttons:**
- **Bold**: Make text bold (`**text**`)
- **Italic**: Make text italic (`*text*`)
- **Heading**: Insert headings (`# H1`, `## H2`, etc.)
- **Quote**: Insert blockquote (`> quote`)
- **List**: Insert unordered list (`- item`)
- **Numbered List**: Insert ordered list (`1. item`)
- **Link**: Insert hyperlink (`[text](url)`)
- **Image**: Insert image (`![alt](url)`)
- **Code**: Insert inline code (`` `code` ``)
- **Preview**: Toggle preview mode

**Editor Features:**
- **Auto-save**: Your work is automatically saved every 30 seconds
- **Split View**: See Markdown and preview side-by-side
- **Syntax Highlighting**: Code blocks are highlighted
- **Paste Images**: Paste images directly from clipboard
- **Keyboard Shortcuts**: Use Ctrl+B for bold, Ctrl+I for italic, etc.

### Saving Your Work

**Draft Mode (Auto-save):**
- Changes are automatically saved to your draft branch
- You can close the editor and return later
- Your draft is private until you publish

**Committing Changes:**
1. Click the "Commit" button
2. Enter a commit message describing your changes
3. Click "Save Commit"
4. Your changes are saved to your draft branch

**Publishing Changes:**
1. After committing, click "Publish"
2. GitWiki will:
   - Check for conflicts with the main branch
   - Merge your changes if there are no conflicts
   - Display a success message

### Creating New Pages

To create a new page:

1. Type the URL for the new page: `/wiki/path/to/new-page`
2. Click "Edit" or use the "Create Page" button
3. Write your content using Markdown
4. Commit and publish your changes

**Best Practices for Page Names:**
- Use lowercase letters
- Separate words with hyphens: `getting-started`
- Organize pages in directories: `docs/api/endpoints`
- Use descriptive names: `installation-guide` not `guide1`

---

## Working with Images

### Uploading Images

**Method 1: Paste from Clipboard**
1. Copy an image to your clipboard
2. In the editor, press Ctrl+V (or Cmd+V on Mac)
3. The image is automatically uploaded
4. Markdown code is inserted: `![image](path/to/image.png)`

**Method 2: Upload Button**
1. Click the "Upload Image" button
2. Select an image file from your computer
3. Wait for upload to complete
4. Markdown code is inserted automatically

**Supported Image Formats:**
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- WebP (`.webp`)
- SVG (`.svg`)

**Image Size Limits:**
- Maximum file size: 10 MB
- Recommended: Optimize images before uploading

### Image Storage

Images are stored in the Git repository:
- Path: `images/{branch_name}/{filename}`
- Versioned like all other content
- Automatically cleaned up when branches are deleted

### Using Images in Pages

```markdown
# Basic image
![Alt text](images/my-image.png)

# Image with title
![Alt text](images/my-image.png "Image title")

# Linked image
[![Alt text](images/my-image.png)](https://example.com)
```

---

## Understanding Conflict Resolution

### What are Conflicts?

Conflicts occur when:
- You edit a page
- Someone else edits the same page
- Both of you try to publish
- The changes overlap or contradict

### How GitWiki Handles Conflicts

When you try to publish and there's a conflict:

1. **Detection**: GitWiki automatically detects conflicts
2. **Notification**: You'll see a conflict resolution screen
3. **Three-Way Diff**: GitWiki shows:
   - **Base**: Original version (before both edits)
   - **Theirs**: Changes published to main
   - **Yours**: Your changes

### Resolving Conflicts

**Using the Visual Diff Tool:**

1. Review all three versions in the diff view
2. Edit the "Resolution" panel to create the final version
3. You can:
   - Keep your changes
   - Accept their changes
   - Combine both changes
   - Write something completely new

4. Click "Resolve and Publish"

**Tips for Conflict Resolution:**
- Read both versions carefully
- Preserve important information from both
- Communicate with the other editor if needed
- Test your resolution if it's complex

### Preventing Conflicts

**Best Practices:**
- Edit one section at a time
- Publish frequently (don't hold drafts for days)
- Communicate with your team about major edits
- Use the activity feed to see who's editing what

---

## Markdown Syntax Guide

### Headings

```markdown
# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
```

### Text Formatting

```markdown
**Bold text**
*Italic text*
~~Strikethrough~~
`Inline code`
```

### Links

```markdown
[Link text](https://example.com)
[Link with title](https://example.com "Link title")
[Internal page link](/wiki/other-page)
```

### Lists

```markdown
# Unordered list
- Item 1
- Item 2
  - Nested item 2.1
  - Nested item 2.2

# Ordered list
1. First item
2. Second item
3. Third item
```

### Code Blocks

````markdown
```python
def hello():
    print("Hello, world!")
```

```javascript
function hello() {
    console.log("Hello, world!");
}
```
````

### Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```

### Blockquotes

```markdown
> This is a blockquote
> It can span multiple lines
>
> And have multiple paragraphs
```

### Horizontal Rules

```markdown
---
or
***
or
___
```

### Task Lists

```markdown
- [x] Completed task
- [ ] Incomplete task
- [ ] Another task
```

---

## Frequently Asked Questions

### Can I edit pages offline?

No, GitWiki requires an active internet connection. However, your drafts are auto-saved frequently, so you won't lose work if you lose connection briefly.

### How long are drafts kept?

Draft branches are kept for 7 days of inactivity by default. After 7 days with no edits, inactive drafts may be automatically cleaned up.

### Can I see who's currently editing?

Check the "Active Sessions" page to see all active edit sessions and who's working on what.

### What happens if I don't publish my draft?

Your draft is saved but not visible to others. You can:
- Come back later and continue editing
- Discard the draft if you change your mind
- Let it expire after 7 days

### Can I undo a published change?

Yes! Use the page history feature:
1. View the page history
2. Find the previous version
3. Copy its content
4. Make a new edit with the old content
5. Publish with a message like "Revert to version X"

### How do I delete a page?

To delete a page:
1. Edit the page
2. Delete all content
3. Commit with message "Delete page"
4. Or keep a redirect: `# Moved\nThis page has moved to [new location](/wiki/new-page)`

### Can I export my wiki?

Yes, the entire wiki is stored as a Git repository. Administrators can:
- Clone the repository
- Export to other formats
- Backup the Git repository

### What happens during a conflict?

Your changes are never lost. You'll be guided through a resolution process where you can:
- See all versions
- Choose which changes to keep
- Combine changes manually

### Is my work backed up?

Yes! Every change is committed to Git, which means:
- Complete version history
- Nothing is ever truly deleted
- Administrators can recover any version
- Optional: Sync to GitHub for remote backup

### Can I use HTML in pages?

By default, raw HTML is escaped for security. Administrators can enable HTML support, but it's not recommended unless necessary.

### How do I report a bug or request a feature?

Contact your GitWiki administrator or file an issue in the GitHub repository if your installation is open-source.

---

## Getting Help

- **Documentation**: Check this guide and other documentation
- **Administrator**: Contact your GitWiki administrator for help
- **Community**: Join the GitWiki community forums
- **GitHub**: Report issues at https://github.com/anthropics/gitwiki

---

*This guide is for GitWiki users. For administrative and technical documentation, see the [Admin Guide](../admin/ADMIN_GUIDE.md) and [Developer Guide](../developer/DEVELOPER_GUIDE.md).*
