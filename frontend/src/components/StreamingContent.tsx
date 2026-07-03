import React from 'react';
import { Typography } from 'antd';

const { Paragraph, Title, Text } = Typography;

interface StreamingContentProps {
  content: string;
}

const StreamingContent: React.FC<StreamingContentProps> = ({ content }) => {
  if (!content) return null;

  // Simple markdown-like rendering
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeContent = '';

    lines.forEach((line, index) => {
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${index}`} style={{
              background: '#f6f8fa',
              padding: 16,
              borderRadius: 8,
              overflow: 'auto',
              fontSize: 13,
              margin: '8px 0',
            }}>
              <code>{codeContent}</code>
            </pre>
          );
          codeContent = '';
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeContent += line + '\n';
        return;
      }

      if (line.startsWith('【重分析标记】')) {
        elements.push(
          <div key={index} style={{ background: '#fff7e6', border: '1px solid #ffd591', color: '#ad6800', padding: '10px 12px', borderRadius: 8, margin: '8px 0 12px 0', fontWeight: 600 }}>
            {line}
          </div>
        );
      } else if (line.startsWith('## ')) {
        elements.push(
          <Title key={index} level={4} style={{ marginTop: 20, marginBottom: 10, color: '#1a365d' }}>
            {line.slice(3)}
          </Title>
        );
      } else if (line.startsWith('### ')) {
        elements.push(
          <Title key={index} level={5} style={{ marginTop: 14, marginBottom: 8, color: '#2d3748' }}>
            {line.slice(4)}
          </Title>
        );
      } else if (line.startsWith('- ')) {
        elements.push(
          <div key={index} style={{ paddingLeft: 16, marginBottom: 4, display: 'flex', gap: 8 }}>
            <span style={{ color: '#3182ce' }}>•</span>
            <span>{line.slice(2)}</span>
          </div>
        );
      } else if (line.trim()) {
        elements.push(
          <Paragraph key={index} style={{ marginBottom: 8, lineHeight: 1.8 }}>
            {line}
          </Paragraph>
        );
      }
    });

    return elements;
  };

  return (
    <div style={{ lineHeight: 1.8 }}>
      {renderContent(content)}
      {!content.endsWith('\n') && <span className="typewriter-cursor" />}
    </div>
  );
};

export default StreamingContent;
