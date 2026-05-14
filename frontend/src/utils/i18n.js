const TRANSLATIONS = {
  en: {
    welcome:
      "Hi, I'm Entitle. Tell me what state you live in, how many people are in your household, and about how much money comes in each month.",
    nav: 'Benefits Navigator',
    tabs: { chat: 'Chat', results: 'Results', docs: 'Docs' },
    offline: 'Local and private',
    inputPlaceholder: 'Type here…',
    noResults: {
      title: 'No results yet',
      desc: 'Start in Chat and share your household size, monthly income, and state. Results will appear here when Entitle has enough information.',
    },
    results: {
      likelyMatches: 'Likely matches',
      benefitsHeader: 'Benefits you may qualify for',
      estimatesNote: 'These are estimates based on what you shared. Use the checklist before applying.',
      monthlyEstimate: 'Monthly estimate',
      varies: 'Varies',
      perYear: '/year',
      annualCredits: 'in annual & seasonal credits',
    },
    doc: {
      title: 'Read a benefits document',
      desc: 'Upload a notice, denial letter, renewal form, or utility bill photo for a plain-language explanation.',
      choose: 'Choose a document photo',
      explain: 'Explain document',
      reading: 'Reading',
      fileHint: 'JPG, PNG, WebP, HEIC, HEIF, or PDF — under 8 MB',
    },
  },
  es: {
    welcome:
      '¡Hola! Soy Entitle. Cuéntame en qué estado vives, cuántas personas hay en tu hogar y aproximadamente cuánto dinero entra al mes.',
    nav: 'Navegador de Beneficios',
    tabs: { chat: 'Chat', results: 'Resultados', docs: 'Docs' },
    offline: 'Local y privado',
    inputPlaceholder: 'Escribe aquí…',
    noResults: {
      title: 'Sin resultados aún',
      desc: 'Comienza en el Chat y comparte el tamaño de tu hogar, ingresos mensuales y estado. Los resultados aparecerán aquí cuando Entitle tenga suficiente información.',
    },
    results: {
      likelyMatches: 'Resultados probables',
      benefitsHeader: 'Beneficios para los que puede calificar',
      estimatesNote: 'Estas son estimaciones basadas en lo que compartió. Use la lista de verificación antes de solicitar.',
      monthlyEstimate: 'Estimación mensual',
      varies: 'Varía',
      perYear: '/año',
      annualCredits: 'en créditos anuales y estacionales',
    },
    doc: {
      title: 'Leer un documento de beneficios',
      desc: 'Sube una notificación, carta de denegación, formulario de renovación o foto de una factura de servicios para una explicación en lenguaje sencillo.',
      choose: 'Elegir foto de documento',
      explain: 'Explicar documento',
      reading: 'Leyendo',
      fileHint: 'JPG, PNG, WebP, HEIC, HEIF o PDF — menos de 8 MB',
    },
  },
  zh: {
    welcome:
      '您好！我是Entitle。请告诉我您住在哪个州、家庭有多少人，以及每月大约有多少收入。',
    nav: '福利导航',
    tabs: { chat: '聊天', results: '结果', docs: '文件' },
    offline: '本地且私密',
    inputPlaceholder: '在此输入…',
    noResults: {
      title: '暂无结果',
      desc: '在聊天中分享您的家庭人数、月收入和所在州，Entitle获得足够信息后结果将显示在此处。',
    },
    results: {
      likelyMatches: '可能符合条件',
      benefitsHeader: '您可能有资格享受的福利',
      estimatesNote: '这些是根据您提供的信息估算的。申请前请核对清单。',
      monthlyEstimate: '每月估算',
      varies: '不等',
      perYear: '/年',
      annualCredits: '年度及季节性补贴',
    },
    doc: {
      title: '阅读福利文件',
      desc: '上传通知、拒绝信、续期表格或水电费账单照片，获取通俗易懂的解释。',
      choose: '选择文件照片',
      explain: '解释文件',
      reading: '正在阅读',
      fileHint: 'JPG、PNG、WebP、HEIC、HEIF 或 PDF — 8 MB以下',
    },
  },
  vi: {
    welcome:
      'Xin chào! Tôi là Entitle. Hãy cho tôi biết bạn sống ở tiểu bang nào, có bao nhiêu người trong gia đình và thu nhập hàng tháng khoảng bao nhiêu.',
    nav: 'Hướng Dẫn Phúc Lợi',
    tabs: { chat: 'Trò chuyện', results: 'Kết quả', docs: 'Tài liệu' },
    offline: 'Cục bộ và riêng tư',
    inputPlaceholder: 'Nhập tại đây…',
    noResults: {
      title: 'Chưa có kết quả',
      desc: 'Bắt đầu trong Trò chuyện và chia sẻ quy mô hộ gia đình, thu nhập hàng tháng và tiểu bang của bạn. Kết quả sẽ xuất hiện ở đây khi Entitle có đủ thông tin.',
    },
    results: {
      likelyMatches: 'Kết quả có thể',
      benefitsHeader: 'Các phúc lợi bạn có thể đủ điều kiện',
      estimatesNote: 'Đây là ước tính dựa trên thông tin bạn cung cấp. Hãy kiểm tra danh sách trước khi nộp đơn.',
      monthlyEstimate: 'Ước tính hàng tháng',
      varies: 'Thay đổi',
      perYear: '/năm',
      annualCredits: 'tín dụng hàng năm và theo mùa',
    },
    doc: {
      title: 'Đọc tài liệu phúc lợi',
      desc: 'Tải lên thông báo, thư từ chối, mẫu gia hạn hoặc hóa đơn tiện ích để được giải thích bằng ngôn ngữ đơn giản.',
      choose: 'Chọn ảnh tài liệu',
      explain: 'Giải thích tài liệu',
      reading: 'Đang đọc',
      fileHint: 'JPG, PNG, WebP, HEIC, HEIF hoặc PDF — dưới 8 MB',
    },
  },
}

export function getTranslations(language) {
  return TRANSLATIONS[language] || TRANSLATIONS.en
}

export function getWelcomeMessage(language) {
  return getTranslations(language).welcome
}
