# Changelog

Todas as alterações relevantes deste projeto são registadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/) e versões segundo [SemVer](https://semver.org/lang/pt-PT/).

## 🎉 Lançamento [1.0.1] - 2026-11-26

### Adicionado
- Vassoura de limpeza no ícone da aplicação (todos os tamanhos) e no cartão principal do Resumo.
- Idiomas: português de Portugal, português do Brasil, espanhol, francês e inglês, com deteção automática do idioma do sistema (outros idiomas usam inglês).
- Atalho do menu e janela de autenticação traduzidos para es e fr.

## [1.0.0] - 2026-11-23

### Adicionado
- Primeira versão da MAINUAN LIMPEZA, com o visual e a disposição de menus do MAINUAN OTIMIZADOR.
- Menu **Resumo** com cartão do espaço total recuperável e caixas com ícone para cada função (utilização do sistema, aplicações, Flatpak, cache do utilizador, lixo, drivers, firmwares, kernels, idiomas, cache APT, temporários e registos).
- Menus: Aplicações, Flatpak, Cache do utilizador, Lixo, Drivers, Firmwares, Kernels, Idiomas, Cache APT, Temporários, Registos e Acerca.
- Sessão de administrador única via `pkexec`/polkit, com validação de caminhos e nomes de pacotes.
- Compatível com Ubuntu 26.04 e mais recentes (`update-initramfs`, pacotes `linux-modules`, deteção de pacotes NVIDIA com versão).
- Proteção do kernel em uso e do mais recente.

## 👤 Autor

Desenvolvido e mantido por David Caixinha.

## 🤝 Contribuir

Para reportar erros ou pedir funcionalidades:
- **Issues**: https://github.com/mainuan/mainuan-limpeza/issues
- **Email**: info@mainuanlinux.com

