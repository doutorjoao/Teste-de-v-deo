// Gera as minutas internas do escritório em Word (.docx):
//  - Autorização de uso de imagem, nome e informações profissionais (equipe)
//  - Termo de confidencialidade e proteção de dados pessoais (associados)
// Uso: node tools/gerar_documentos.js   →  arquivos em documentos/
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, Header, Footer,
  PageNumber, BorderStyle, ShadingType, TabStopType,
} = require('docx');

const OUT = path.join(__dirname, '..', 'documentos');
fs.mkdirSync(OUT, { recursive: true });

const GOLD = '8E6A2F';
const FONT = 'Times New Roman';
const BLANK = '____________________';
const ESCRITORIO = {
  nome: 'JOÃO PEDRO GOMES DOS SANTOS',
  oab: 'OAB/SE 17.295',
  email: 'joaopedrogomes2322@gmail.com',
  site: 'joaopedrogomesadvhacker.adv.br',
  instagram: '@advogadoohacker',
};

// ---------- blocos de texto ----------
const t = (text, o = {}) => new TextRun({ text, font: FONT, size: 24, ...o });
const p = (runs, o = {}) => new Paragraph({
  children: Array.isArray(runs) ? runs : [t(runs)],
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 160, line: 360 },
  ...o,
});
const title = (text) => new Paragraph({
  children: [t(text, { bold: true, size: 28 })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 360 },
});
const clause = (text) => new Paragraph({
  children: [t(text, { bold: true })],
  spacing: { before: 280, after: 120 },
  keepNext: true,
});
const item = (label, text) => p([t(label + ' ', { bold: true }), t(text)], { indent: { left: 360 } });
const note = (text) => new Paragraph({
  children: [t(text, { size: 20, italics: true, color: '5D574B' })],
  alignment: AlignmentType.LEFT,
  spacing: { after: 280 },
  border: {
    top: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 },
    bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 },
    left: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 },
    right: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 },
  },
  shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'F6F0E2' },
});
// linha, nome e função ficam sempre juntos na mesma página
const signature = (name, role) => [
  new Paragraph({ children: [t('')], spacing: { before: 600 }, keepNext: true }),
  new Paragraph({
    children: [t('_______________________________________________')],
    alignment: AlignmentType.CENTER, spacing: { after: 40 }, keepNext: true,
  }),
  new Paragraph({ children: [t(name, { bold: true })], alignment: AlignmentType.CENTER, spacing: { after: 20 }, keepNext: true }),
  new Paragraph({ children: [t(role, { size: 22 })], alignment: AlignmentType.CENTER, spacing: { after: 120 } }),
];
const witnesses = () => [
  new Paragraph({ children: [t('Testemunhas:', { bold: true })], spacing: { before: 480, after: 240 }, keepNext: true }),
  new Paragraph({
    children: [t('1. _____________________________\tCPF: ____________________')],
    tabStops: [{ type: TabStopType.LEFT, position: 5200 }], spacing: { after: 360 },
  }),
  new Paragraph({
    children: [t('2. _____________________________\tCPF: ____________________')],
    tabStops: [{ type: TabStopType.LEFT, position: 5200 }], spacing: { after: 120 },
  }),
];
const placeDate = () => p('Aracaju/SE, _____ de ____________________ de 20____.', { alignment: AlignmentType.RIGHT, spacing: { before: 360, after: 120 } });

const header = new Header({
  children: [new Paragraph({
    children: [
      t('JOÃO PEDRO GOMES', { bold: true, color: GOLD, size: 18, characterSpacing: 40 }),
      t('  ·  Direito Digital e Crimes Cibernéticos  ·  OAB/SE 17.295', { color: GOLD, size: 18 }),
    ],
    alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 } },
  })],
});
const footer = new Footer({
  children: [new Paragraph({
    children: [
      t('Documento interno · ', { size: 16, color: '7D786D' }),
      t('Página ', { size: 16, color: '7D786D' }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '7D786D' }),
      t(' de ', { size: 16, color: '7D786D' }),
      new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: '7D786D' }),
    ],
    alignment: AlignmentType.CENTER,
  })],
});

const build = (children) => new Document({
  creator: 'João Pedro Gomes — Advocacia',
  styles: { default: { document: { run: { font: FONT, size: 24 } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1417, bottom: 1417, left: 1701, right: 1134, header: 708, footer: 708 } } },
    headers: { default: header },
    footers: { default: footer },
    children,
  }],
});

const NOTA = 'MINUTA PARA REVISÃO — Revise o texto, preencha os campos em branco e apague esta nota antes da assinatura.';

// ---------- equipe ----------
const equipe = [
  { arquivo: 'Camila-Porto-Melo', nome: 'CAMILA PORTO MELO', genero: 'f', profissao: 'designer', oab: null, papel: 'Cofundadora — design e comunicação' },
  { arquivo: 'Guilherme-Shai-Albuquerque-Pereira', nome: 'GUILHERME SHAI ALBUQUERQUE PEREIRA', genero: 'm', profissao: 'advogado', oab: 'OAB/SE 18.717', papel: 'Advogado associado' },
  { arquivo: 'Wanderlei-Ribeiro-de-Azevedo-Junior', nome: 'WANDERLEI RIBEIRO DE AZEVEDO JUNIOR', genero: 'm', profissao: 'advogado', oab: 'OAB/SE 16.134', papel: 'Advogado associado' },
  { arquivo: 'Isaac-Nunliver-Nunes-de-Oliveira', nome: 'ISAAC NUNLIVER NUNES DE OLIVEIRA', genero: 'm', profissao: 'advogado', oab: 'OAB/SE 15.037', papel: 'Advogado associado' },
];

const qualificacao = (x) => {
  const ins = x.oab ? `${x.profissao} inscrito na ${x.oab.replace('OAB/SE ', 'OAB/SE sob o nº ')}` : x.profissao;
  return `${x.nome}, nacionalidade ${BLANK}, estado civil ${BLANK}, ${ins}, inscrit${x.genero === 'f' ? 'a' : 'o'} no CPF sob o nº ${BLANK}, residente e domiciliad${x.genero === 'f' ? 'a' : 'o'} em ${BLANK}${BLANK}`;
};
const escritorioQualif = `${ESCRITORIO.nome}, advogado inscrito na OAB/SE sob o nº 17.295, inscrito no CPF sob o nº ${BLANK}, com escritório profissional em Aracaju/SE, endereço ${BLANK}${BLANK}`;

// ---------- 1. Autorização de uso de imagem ----------
function autorizacao(x) {
  const o = x.genero === 'f' ? 'a' : 'o';
  const A = `AUTORIZANTE`;
  return build([
    note(NOTA),
    title('AUTORIZAÇÃO DE USO DE IMAGEM, NOME E INFORMAÇÕES PROFISSIONAIS'),
    p([t(`${A}: `, { bold: true }), t(qualificacao(x) + '.')]),
    p([t('AUTORIZADO: ', { bold: true }), t(escritorioQualif + ', doravante denominado ESCRITÓRIO.')]),
    p(`Pelo presente instrumento, ${o} ${A} autoriza o ESCRITÓRIO a utilizar sua imagem, seu nome e suas informações profissionais, nas condições a seguir.`),

    clause('CLÁUSULA 1ª — DO OBJETO'),
    p(`1.1. Esta autorização abrange o uso, pelo ESCRITÓRIO, dos seguintes elementos relativos ${x.genero === 'f' ? 'à' : 'ao'} ${A}:`),
    item('a)', 'imagem, por meio de fotografias e, quando houver, vídeos;'),
    item('b)', x.oab ? 'nome completo e número de inscrição na Ordem dos Advogados do Brasil;' : 'nome completo;'),
    item('c)', `informações profissionais, como formação, áreas de atuação, trajetória e textos de apresentação aprovados previamente pel${o} ${A}.`),

    clause('CLÁUSULA 2ª — DA FINALIDADE E DOS MEIOS'),
    p(`2.1. O uso destina-se exclusivamente à divulgação institucional do ESCRITÓRIO e da equipe, em especial: (i) no site ${ESCRITORIO.site}; (ii) nos perfis do ESCRITÓRIO em redes sociais, inclusive o Instagram ${ESCRITORIO.instagram}; e (iii) em materiais de divulgação digitais ou impressos, como publicações, stories, cartões e apresentações.`),
    p('2.2. É vedado o uso para finalidade diversa da prevista nesta cláusula, bem como qualquer uso que atente contra a honra, a imagem ou a reputação ' + (x.genero === 'f' ? 'da' : 'do') + ` ${A}.`),
    p('2.3. As publicações observarão as normas de publicidade da advocacia, em especial o Código de Ética e Disciplina da OAB e o Provimento nº 205/2021 do Conselho Federal da OAB.'),

    clause('CLÁUSULA 3ª — DA EDIÇÃO'),
    p('3.1. O ESCRITÓRIO poderá realizar recortes, ajustes de cor, de enquadramento e de formatação compatíveis com sua identidade visual, sem alterações que distorçam a imagem ' + (x.genero === 'f' ? 'da' : 'do') + ` ${A}.`),
    p(`3.2. Textos de apresentação e informações profissionais somente serão publicados ou alterados com a aprovação d${o} ${A}, que poderá ser dada por e-mail ou mensagem.`),

    clause('CLÁUSULA 4ª — DA GRATUIDADE'),
    p('4.1. Esta autorização é concedida a título gratuito, sem qualquer contraprestação, a qualquer tempo.'),

    clause('CLÁUSULA 5ª — DO PRAZO E DA REVOGAÇÃO'),
    p(`5.1. Esta autorização vigora por prazo indeterminado, enquanto perdurar a colaboração entre ${o} ${A} e o ESCRITÓRIO.`),
    p(`5.2. ${o.toUpperCase() === 'A' ? 'A' : 'O'} ${A} poderá revogar esta autorização a qualquer tempo, mediante comunicação escrita, inclusive por e-mail. Nesse caso, o ESCRITÓRIO removerá a imagem, o nome e as informações profissionais do site e dos perfis sob seu controle em até 15 (quinze) dias do recebimento da comunicação.`),
    p('5.3. Encerrada a colaboração, aplica-se o prazo de remoção da cláusula 5.2, contado do encerramento, salvo nova autorização expressa.'),
    p('5.4. A revogação não alcança materiais impressos já distribuídos nem conteúdos compartilhados por terceiros antes da revogação, mas o ESCRITÓRIO não fará novas distribuições ou publicações.'),

    clause('CLÁUSULA 6ª — DA PROTEÇÃO DE DADOS PESSOAIS'),
    p(`6.1. O tratamento dos dados pessoais abrangidos por esta autorização tem como base legal o consentimento (art. 7º, I, da Lei nº 13.709/2018 — LGPD) e se limita às finalidades aqui descritas.`),
    p(`6.2. ${o.toUpperCase() === 'A' ? 'A' : 'O'} ${A} pode revogar o consentimento a qualquer momento (art. 8º, § 5º, da LGPD) e exercer os direitos previstos no art. 18 da LGPD pelo canal do encarregado: ${ESCRITORIO.email}.`),

    clause('CLÁUSULA 7ª — DO FORO'),
    p('7.1. Fica eleito o foro da Comarca de Aracaju/SE para dirimir eventuais questões decorrentes desta autorização.'),

    p('E, por estarem de acordo, as partes assinam este instrumento em 2 (duas) vias de igual teor.', { spacing: { before: 280, after: 120, line: 360 } }),
    placeDate(),
    ...signature(x.nome, `${A}${x.oab ? ' · ' + x.oab : ''}`),
    ...signature(ESCRITORIO.nome, `ESCRITÓRIO · ${ESCRITORIO.oab}`),
    ...witnesses(),
  ]);
}

// ---------- 2. Termo de confidencialidade e proteção de dados (associados) ----------
function confidencialidade(x) {
  return build([
    note(NOTA + ' Se já houver contrato de associação registrado na OAB/SE, este termo pode ser anexado a ele.'),
    title('TERMO DE CONFIDENCIALIDADE E PROTEÇÃO DE DADOS PESSOAIS'),
    p([t('ESCRITÓRIO: ', { bold: true }), t(escritorioQualif + ', controlador e encarregado pelo tratamento de dados pessoais do escritório.')]),
    p([t('ASSOCIADO: ', { bold: true }), t(qualificacao(x) + '.')]),

    clause('CONSIDERANDO QUE:'),
    item('(i)', 'o ASSOCIADO atua em colaboração com o ESCRITÓRIO, em regime de associação;'),
    item('(ii)', 'no exercício dessa atuação, o ASSOCIADO terá acesso a informações sigilosas de clientes e a dados pessoais, inclusive dados pessoais sensíveis;'),
    item('(iii)', 'o advogado está sujeito ao dever de sigilo profissional previsto na Lei nº 8.906/1994 (Estatuto da Advocacia) e no Código de Ética e Disciplina da OAB, e o tratamento de dados pessoais é regido pela Lei nº 13.709/2018 (LGPD);'),
    p('as partes resolvem firmar o presente Termo, nas seguintes condições:'),

    clause('CLÁUSULA 1ª — DO OBJETO'),
    p('1.1. Este Termo estabelece as obrigações de confidencialidade e de proteção de dados pessoais a serem observadas pelo ASSOCIADO em relação às informações a que tiver acesso em razão da colaboração com o ESCRITÓRIO.'),

    clause('CLÁUSULA 2ª — DAS INFORMAÇÕES CONFIDENCIAIS'),
    p('2.1. Consideram-se confidenciais, independentemente da forma ou do meio em que estejam (oral, escrita, digital, áudio, imagem ou vídeo): as informações sobre clientes e seus casos, documentos, provas, estratégias e peças; os dados pessoais e os dados pessoais sensíveis de clientes e de terceiros; as informações internas, financeiras e comerciais do ESCRITÓRIO; e as credenciais de acesso a sistemas, contas e dispositivos.'),

    clause('CLÁUSULA 3ª — DAS OBRIGAÇÕES DE CONFIDENCIALIDADE'),
    p('3.1. O ASSOCIADO se obriga a:'),
    item('a)', 'utilizar as informações confidenciais exclusivamente para a prestação dos serviços jurídicos relacionados ao ESCRITÓRIO;'),
    item('b)', 'não divulgar informações confidenciais a terceiros sem autorização, ressalvadas as hipóteses de obrigação legal ou ordem judicial, caso em que comunicará o ESCRITÓRIO previamente, sempre que permitido;'),
    item('c)', 'restringir o acesso às informações às pessoas que dele necessitem para atuar no caso;'),
    item('d)', 'não comentar casos ou expor clientes em redes sociais, grupos de mensagens, eventos ou conversas com terceiros, ainda que sem citar nomes, quando for possível identificá-los;'),
    item('e)', 'observar o dever de sigilo profissional previsto no Estatuto da Advocacia (art. 34, VII) e no Código de Ética e Disciplina da OAB (arts. 35 a 38).'),

    clause('CLÁUSULA 4ª — DA PROTEÇÃO DE DADOS PESSOAIS'),
    p('4.1. O ASSOCIADO se obriga a:'),
    item('a)', 'tratar dados pessoais apenas para as finalidades do atendimento jurídico, em conformidade com a LGPD e com as orientações do ESCRITÓRIO;'),
    item('b)', 'tratar somente os dados necessários a cada finalidade, evitando coletar ou guardar informações desnecessárias;'),
    item('c)', 'adotar cuidado redobrado com dados pessoais sensíveis, como informações sobre saúde, vida sexual, imagens íntimas e dados de crianças e adolescentes;'),
    item('d)', 'não armazenar nem transferir dados de clientes para contas, nuvens ou dispositivos pessoais não autorizados pelo ESCRITÓRIO;'),
    item('e)', 'não inserir dados que permitam identificar clientes em ferramentas públicas de inteligência artificial ou em serviços on-line não autorizados pelo ESCRITÓRIO;'),
    item('f)', 'encaminhar ao encarregado do ESCRITÓRIO, em até 2 (dois) dias úteis, qualquer solicitação de titular de dados que receber.'),

    clause('CLÁUSULA 5ª — DAS MEDIDAS DE SEGURANÇA'),
    p('5.1. Nos dispositivos e contas utilizados no trabalho, o ASSOCIADO manterá, no mínimo: senha forte ou biometria e bloqueio automático de tela; verificação em duas etapas no e-mail, no WhatsApp e nos serviços de armazenamento em nuvem; sistemas e aplicativos atualizados; e cautela no uso de redes Wi-Fi públicas para acessar informações de clientes.'),
    p('5.2. O compartilhamento de documentos de clientes será feito pelos canais definidos pelo ESCRITÓRIO.'),

    clause('CLÁUSULA 6ª — DOS INCIDENTES DE SEGURANÇA'),
    p('6.1. O ASSOCIADO comunicará ao ESCRITÓRIO, em até 24 (vinte e quatro) horas da ciência, qualquer incidente que possa afetar informações confidenciais ou dados pessoais, como perda ou furto de dispositivo, acesso indevido a contas, envio de mensagem ou documento ao destinatário errado ou suspeita de invasão.'),
    p('6.2. O ASSOCIADO colaborará com as medidas de contenção e com as comunicações que o ESCRITÓRIO deva fazer à Autoridade Nacional de Proteção de Dados (ANPD) e aos titulares, nos termos do art. 48 da LGPD.'),

    clause('CLÁUSULA 7ª — DA DEVOLUÇÃO E DA ELIMINAÇÃO'),
    p('7.1. Encerrada a colaboração, ou a pedido do ESCRITÓRIO, o ASSOCIADO devolverá ou eliminará as informações confidenciais e os dados pessoais em seu poder, ressalvados aqueles que deva manter por obrigação legal, e confirmará por escrito a providência.'),

    clause('CLÁUSULA 8ª — DA VIGÊNCIA'),
    p('8.1. Este Termo vigora a partir da assinatura e durante toda a colaboração. As obrigações de confidencialidade e de sigilo profissional permanecem válidas após o encerramento da colaboração, por prazo indeterminado.'),

    clause('CLÁUSULA 9ª — DAS RESPONSABILIDADES'),
    p('9.1. O descumprimento deste Termo sujeitará o ASSOCIADO à reparação dos danos causados, inclusive em ação de regresso (art. 42 da LGPD), sem prejuízo da apuração de eventual infração disciplinar perante a OAB e das demais sanções cabíveis.'),

    clause('CLÁUSULA 10ª — DISPOSIÇÕES GERAIS'),
    p('10.1. Este Termo complementa o contrato de associação existente entre as partes. Em caso de conflito, prevalecerá a disposição que oferecer maior proteção às informações confidenciais e aos dados pessoais.'),
    p('10.2. Alterações deste Termo somente terão validade se feitas por escrito.'),
    p('10.3. Fica eleito o foro da Comarca de Aracaju/SE para dirimir eventuais questões decorrentes deste Termo.'),

    p('E, por estarem de acordo, as partes assinam este Termo em 2 (duas) vias de igual teor.', { spacing: { before: 280, after: 120, line: 360 } }),
    placeDate(),
    ...signature(ESCRITORIO.nome, `ESCRITÓRIO · ${ESCRITORIO.oab}`),
    ...signature(x.nome, `ASSOCIADO · ${x.oab}`),
    ...witnesses(),
  ]);
}

(async () => {
  const jobs = [];
  for (const x of equipe) {
    jobs.push([`Autorizacao-Uso-de-Imagem-${x.arquivo}.docx`, autorizacao(x)]);
    if (x.oab) jobs.push([`Termo-Confidencialidade-LGPD-${x.arquivo}.docx`, confidencialidade(x)]);
  }
  for (const [name, doc] of jobs) {
    fs.writeFileSync(path.join(OUT, name), await Packer.toBuffer(doc));
    console.log('gerado', name);
  }
})();
